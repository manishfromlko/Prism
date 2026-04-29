"""
Profile indexer: generates user profiles from the ingestion catalog and
stores them in the Milvus user_profiles collection.

Usage:
    python -m src.retrieval.profile_indexer \
        --catalog dataset/.ingestion/ingestion_catalog.json
"""

import argparse
import logging
import os
import sys

from .config import RetrievalConfig
from .embeddings import EmbeddingService
from .user_profile_generator import generate_profiles
from .user_profile_store import UserProfileStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_profile_indexing(catalog_path: str) -> dict:
    config = RetrievalConfig.from_env()
    store = UserProfileStore(config)
    store.create_collection(drop_if_exists=True)

    logger.info("Generating user profiles from catalog...")
    profiles = generate_profiles(catalog_path)
    logger.info(f"Generated {len(profiles)} profiles")

    embedder = EmbeddingService(config)
    texts = [p["user_profile"] for p in profiles]
    logger.info("Embedding profile texts...")
    vectors = embedder.generate_embeddings(texts)

    for p, vec in zip(profiles, vectors):
        p["vector"] = vec

    inserted = store.upsert_profiles(profiles)
    return {"inserted": inserted, "total": len(profiles)}


def main():
    parser = argparse.ArgumentParser(description="Index user profiles into Milvus")
    parser.add_argument(
        "--catalog",
        default=os.getenv("INGESTION_CATALOG_PATH", "dataset/.ingestion/ingestion_catalog.json"),
    )
    args = parser.parse_args()

    if not os.path.exists(args.catalog):
        print(f"ERROR: catalog not found: {args.catalog}", file=sys.stderr)
        sys.exit(1)

    result = run_profile_indexing(args.catalog)
    print(f"\nDone — inserted: {result['inserted']}, total users: {result['total']}")


if __name__ == "__main__":
    main()
