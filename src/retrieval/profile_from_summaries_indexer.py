"""
Profile-from-summaries indexer: generates user profiles by using pre-indexed
artifact summaries from Milvus as LLM context, then stores the resulting
profiles in the user_profiles collection.

This is the preferred indexer on branch 006-user-profiles-with-llm.
It requires artifact_summaries to be populated first.

Usage:
    # Step 1 — populate artifact summaries (if not already done):
    python -m src.retrieval.artifact_summary_indexer \\
        --catalog dataset/.ingestion/ingestion_catalog.json --mode full

    # Step 2 — generate and index user profiles:
    python -m src.retrieval.profile_from_summaries_indexer
"""

import argparse
import logging
import os
import sys

from .config import RetrievalConfig
from .embeddings import EmbeddingService
from .user_profile_from_summaries_generator import generate_profiles_from_summaries
from .user_profile_store import UserProfileStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_profile_indexing_from_summaries(drop_existing: bool = True) -> dict:
    """
    Generate user profiles from Milvus artifact summaries and index them into
    the user_profiles collection.

    Args:
        drop_existing: Drop and recreate the user_profiles collection before
                       inserting (True = full rebuild, False = upsert in place).
    """
    config = RetrievalConfig.from_env()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to the .env file at the project root.")

    model = os.getenv("PROFILE_LLM_MODEL", config.profile_llm_model)

    logger.info(f"Generating user profiles from artifact summaries using model={model}...")
    profiles = generate_profiles_from_summaries(
        config=config,
        openai_api_key=api_key,
        model=model,
    )

    if not profiles:
        logger.warning("No profiles generated — check that artifact_summaries collection is populated.")
        return {"inserted": 0, "total": 0}

    logger.info(f"Generated {len(profiles)} profiles — embedding profile texts...")
    embedder = EmbeddingService(config)
    texts = [p["user_profile"] for p in profiles]
    vectors = embedder.generate_embeddings(texts)
    for p, vec in zip(profiles, vectors):
        p["vector"] = vec

    store = UserProfileStore(config)
    store.create_collection(drop_if_exists=drop_existing)
    inserted = store.upsert_profiles(profiles)

    logger.info(f"Done — inserted {inserted} user profiles into Milvus.")
    return {"inserted": inserted, "total": len(profiles)}


def main():
    parser = argparse.ArgumentParser(
        description="Index user profiles (from artifact summaries) into Milvus"
    )
    parser.add_argument(
        "--no-drop",
        action="store_true",
        default=False,
        help="Upsert into the existing collection instead of dropping and recreating it.",
    )
    args = parser.parse_args()

    result = run_profile_indexing_from_summaries(drop_existing=not args.no_drop)
    print(f"\nDone — inserted: {result['inserted']}, total users: {result['total']}")


if __name__ == "__main__":
    main()
