"""
Profile-from-summaries indexer: generates user profiles by using pre-indexed
artifact summaries from Qdrant as LLM context, then stores the resulting
profiles in the user_profiles collection.

This is the preferred indexer on branch 006-user-profiles-with-llm.
It requires artifact_summaries to be populated first.

Usage:
    # Step 1 — populate artifact summaries (if not already done):
    python -m src.retrieval.artifact_summary_indexer \\
        --mode full

    # Step 2 — generate and index user profiles:
    python -m src.retrieval.profile_from_summaries_indexer
"""

import argparse
import logging
import os
import sys
from typing import Iterable, Optional, Set

from .config import RetrievalConfig
from .embeddings import EmbeddingService
from .user_profile_from_summaries_generator import generate_profiles_from_summaries
from .user_profile_store import UserProfileStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _normalize_user_ids(user_ids: Optional[Iterable[str]]) -> Optional[Set[str]]:
    if user_ids is None:
        return None
    normalized = {user_id.strip() for user_id in user_ids if user_id and user_id.strip()}
    return normalized or set()


def run_profile_indexing_from_summaries(
    drop_existing: bool = False,
    user_ids: Optional[Iterable[str]] = None,
) -> dict:
    """
    Generate user profiles from Qdrant artifact summaries and index them into
    the user_profiles collection.

    Args:
        drop_existing: Drop and recreate the user_profiles collection before
                       inserting (True = full rebuild, False = upsert in place).
    """
    config = RetrievalConfig.from_env()

    model = os.getenv("PROFILE_LLM_MODEL", config.profile_llm_model)

    target_user_ids = _normalize_user_ids(user_ids)
    if target_user_ids == set():
        logger.info("No target users supplied for profile indexing; nothing to do.")
        return {"inserted": 0, "deleted": 0, "total": 0, "target_user_ids": []}

    if target_user_ids is None:
        logger.info(f"Generating all user profiles from artifact summaries using model={model}...")
    else:
        logger.info(
            f"Generating {len(target_user_ids)} user profiles from artifact summaries "
            f"using model={model}..."
        )

    profiles = generate_profiles_from_summaries(
        config=config,
        model=model,
        user_ids=target_user_ids,
    )

    store = UserProfileStore(config)
    store.create_collection(drop_if_exists=drop_existing)

    deleted = 0
    if target_user_ids is not None:
        generated_user_ids = {profile["user_id"] for profile in profiles}
        users_without_summaries = sorted(target_user_ids - generated_user_ids)
        deleted = store.delete_profiles(users_without_summaries)

    if not profiles:
        logger.warning("No profiles generated — check that artifact_summaries collection is populated.")
        return {
            "inserted": 0,
            "deleted": deleted,
            "total": 0,
            "target_user_ids": sorted(target_user_ids) if target_user_ids is not None else None,
        }

    logger.info(f"Generated {len(profiles)} profiles — embedding profile texts...")
    embedder = EmbeddingService(config)
    texts = [p["user_profile"] for p in profiles]
    vectors = embedder.generate_embeddings(texts)
    for p, vec in zip(profiles, vectors):
        p["vector"] = vec

    inserted = store.upsert_profiles(profiles)

    logger.info(f"Done - inserted {inserted} user profiles into Qdrant.")
    return {
        "inserted": inserted,
        "deleted": deleted,
        "total": len(profiles),
        "target_user_ids": sorted(target_user_ids) if target_user_ids is not None else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Index user profiles (from artifact summaries) into Qdrant"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        default=False,
        help="Drop and recreate the user_profiles collection before indexing.",
    )
    parser.add_argument(
        "--user-ids",
        default="",
        help="Comma-separated user/workspace IDs to regenerate. Omit to index all users.",
    )
    args = parser.parse_args()

    user_ids = [value.strip() for value in args.user_ids.split(",") if value.strip()] or None
    result = run_profile_indexing_from_summaries(
        drop_existing=args.drop,
        user_ids=user_ids,
    )
    print(
        f"\nDone — inserted: {result['inserted']}, "
        f"deleted: {result.get('deleted', 0)}, "
        f"total users: {result['total']}"
    )


if __name__ == "__main__":
    main()
