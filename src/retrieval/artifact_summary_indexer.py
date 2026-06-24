"""
Artifact summary indexer: generates artifact summaries from ingestion catalog and
stores them in the Qdrant artifact_summaries collection.

Usage:
    python -m src.retrieval.artifact_summary_indexer \
        --catalog dataset/.ingestion/ingestion_catalog.json \
        --mode incremental
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, Set

from .artifact_summary_generator import generate_artifact_summaries
from .artifact_summary_store import ArtifactSummaryStore
from .config import RetrievalConfig
from .embeddings import EmbeddingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


ELIGIBLE_FILE_TYPES = {"notebook", "script", "text"}


def _load_eligible_artifacts(catalog_path: str) -> Dict[str, Dict]:
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    return {
        artifact.get("artifact_id", ""): artifact
        for artifact in catalog.get("artifacts", {}).values()
        if artifact.get("artifact_id")
        and artifact.get("workspace_id")
        and artifact.get("file_type") in ELIGIBLE_FILE_TYPES
    }


def _select_incremental_artifacts(
    artifacts: Dict[str, Dict],
    existing_summaries: Dict[str, Dict],
    store: ArtifactSummaryStore,
) -> tuple[Set[str], Set[str], int, int]:
    """Return artifact IDs to summarize, affected users, skipped count, stale count."""
    catalog_ids = set(artifacts)
    existing_ids = set(existing_summaries)
    stale_ids = sorted(existing_ids - catalog_ids)
    affected_user_ids: Set[str] = {
        existing_summaries[artifact_id].get("user_id", "")
        for artifact_id in stale_ids
        if existing_summaries[artifact_id].get("user_id")
    }
    if stale_ids:
        store.delete_summaries(stale_ids)

    to_summarize: Set[str] = set()
    missing_hash_backfill: Dict[str, str] = {}
    skipped = 0
    for artifact_id, artifact in artifacts.items():
        current_hash = artifact.get("content_hash", "")
        existing = existing_summaries.get(artifact_id)
        if not existing:
            to_summarize.add(artifact_id)
            affected_user_ids.add(artifact.get("workspace_id", ""))
            continue

        existing_hash = existing.get("content_hash", "")
        if existing_hash and existing_hash == current_hash:
            skipped += 1
            continue

        if not existing_hash and current_hash:
            missing_hash_backfill[artifact_id] = current_hash
            skipped += 1
            continue

        to_summarize.add(artifact_id)
        affected_user_ids.add(artifact.get("workspace_id", ""))

    backfilled = store.set_content_hashes(missing_hash_backfill)
    return to_summarize, affected_user_ids, skipped, len(stale_ids) + backfilled


def run_artifact_summary_indexing(catalog_path: str, mode: str = "incremental") -> Dict:
    config = RetrievalConfig.from_env()
    store = ArtifactSummaryStore(config)
    store.create_collection(drop_if_exists=(mode == "full"))

    artifacts = _load_eligible_artifacts(catalog_path)
    if mode == "incremental":
        existing_summaries = store.get_summary_index(limit=max(10000, len(artifacts) * 2))
        artifact_ids, affected_user_ids, skipped, maintenance_count = _select_incremental_artifacts(
            artifacts=artifacts,
            existing_summaries=existing_summaries,
            store=store,
        )
        logger.info(
            "Incremental artifact summary sync: "
            f"{len(artifact_ids)} changed/new, {skipped} unchanged, "
            f"{maintenance_count} maintenance updates"
        )
        if not artifact_ids:
            return {
                "inserted": 0,
                "total": len(artifacts),
                "skipped": skipped,
                "changed_artifact_ids": [],
                "affected_user_ids": sorted(affected_user_ids),
                "maintenance_updates": maintenance_count,
            }
    else:
        artifact_ids = set(artifacts)
        affected_user_ids = {
            artifact.get("workspace_id", "")
            for artifact in artifacts.values()
            if artifact.get("workspace_id")
        }
        skipped = 0
        maintenance_count = 0

    model = os.getenv("ARTIFACT_SUMMARY_LLM_MODEL", config.profile_llm_model)
    temperature = float(os.getenv("ARTIFACT_SUMMARY_LLM_TEMPERATURE", "0.0"))
    max_tokens = int(os.getenv("ARTIFACT_SUMMARY_LLM_MAX_TOKENS", "220"))
    top_p = float(os.getenv("ARTIFACT_SUMMARY_LLM_TOP_P", "1.0"))
    frequency_penalty = float(os.getenv("ARTIFACT_SUMMARY_LLM_FREQUENCY_PENALTY", "0.0"))
    presence_penalty = float(os.getenv("ARTIFACT_SUMMARY_LLM_PRESENCE_PENALTY", "0.0"))

    logger.info("Generating artifact summaries from catalog...")
    summaries = generate_artifact_summaries(
        catalog_path=catalog_path,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        artifact_ids=artifact_ids,
    )
    logger.info(f"Generated {len(summaries)} artifact summaries")

    if not summaries:
        return {
            "inserted": 0,
            "total": len(artifacts),
            "skipped": skipped,
            "changed_artifact_ids": sorted(artifact_ids),
            "affected_user_ids": sorted(affected_user_ids),
            "maintenance_updates": maintenance_count,
        }

    embedder = EmbeddingService(config)
    texts = [s["artifact_summary"] for s in summaries]
    logger.info("Embedding artifact summaries...")
    vectors = embedder.generate_embeddings(texts)
    for summary, vector in zip(summaries, vectors):
        summary["vector"] = vector

    inserted = store.upsert_summaries(summaries)
    return {
        "inserted": inserted,
        "total": len(artifacts),
        "skipped": skipped,
        "changed_artifact_ids": sorted(artifact_ids),
        "affected_user_ids": sorted(affected_user_ids),
        "maintenance_updates": maintenance_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Index artifact summaries into Qdrant")
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
    print(
        f"\nDone - inserted: {result['inserted']}, "
        f"skipped: {result.get('skipped', 0)}, "
        f"total artifacts: {result['total']}, "
        f"affected users: {len(result.get('affected_user_ids', []))}"
    )


if __name__ == "__main__":
    main()
