"""
Artifact summary indexer: generates artifact summaries from ingestion catalog and
stores them in the Milvus artifact_summaries collection.

Usage:
    python -m src.retrieval.artifact_summary_indexer \
        --catalog dataset/.ingestion/ingestion_catalog.json \
        --mode incremental
"""

import argparse
import logging
import os
import sys
from typing import Dict

from .artifact_summary_generator import generate_artifact_summaries
from .artifact_summary_store import ArtifactSummaryStore
from .config import RetrievalConfig
from .embeddings import EmbeddingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_artifact_summary_indexing(catalog_path: str, mode: str = "incremental") -> Dict:
    config = RetrievalConfig.from_env()
    store = ArtifactSummaryStore(config)
    store.create_collection(drop_if_exists=(mode == "full"))

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to the .env file at the project root.")

    model = os.getenv("ARTIFACT_SUMMARY_LLM_MODEL", config.profile_llm_model)
    temperature = float(os.getenv("ARTIFACT_SUMMARY_LLM_TEMPERATURE", "0.0"))
    max_tokens = int(os.getenv("ARTIFACT_SUMMARY_LLM_MAX_TOKENS", "220"))
    top_p = float(os.getenv("ARTIFACT_SUMMARY_LLM_TOP_P", "1.0"))
    frequency_penalty = float(os.getenv("ARTIFACT_SUMMARY_LLM_FREQUENCY_PENALTY", "0.0"))
    presence_penalty = float(os.getenv("ARTIFACT_SUMMARY_LLM_PRESENCE_PENALTY", "0.0"))

    logger.info("Generating artifact summaries from catalog...")
    summaries = generate_artifact_summaries(
        catalog_path=catalog_path,
        openai_api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
    )
    logger.info(f"Generated {len(summaries)} artifact summaries")

    embedder = EmbeddingService(config)
    texts = [s["artifact_summary"] for s in summaries]
    logger.info("Embedding artifact summaries...")
    vectors = embedder.generate_embeddings(texts)
    for summary, vector in zip(summaries, vectors):
        summary["vector"] = vector

    inserted = store.upsert_summaries(summaries)
    return {"inserted": inserted, "total": len(summaries)}


def main():
    parser = argparse.ArgumentParser(description="Index artifact summaries into Milvus")
    parser.add_argument(
        "--catalog",
        default=os.getenv("INGESTION_CATALOG_PATH", "dataset/.ingestion/ingestion_catalog.json"),
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
    )
    args = parser.parse_args()

    if not os.path.exists(args.catalog):
        print(f"ERROR: catalog not found: {args.catalog}", file=sys.stderr)
        sys.exit(1)

    result = run_artifact_summary_indexing(args.catalog, args.mode)
    print(f"\nDone - inserted: {result['inserted']}, total artifacts: {result['total']}")


if __name__ == "__main__":
    main()
