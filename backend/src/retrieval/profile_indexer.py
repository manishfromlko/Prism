"""Profile indexer: generates user profiles from Postgres artifact metadata."""

import argparse
import logging

from .config import RetrievalConfig
from .embeddings import EmbeddingService
from .metadata_repository import MetadataRepository
from .user_profile_generator import generate_profiles
from .user_profile_store import UserProfileStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_profile_indexing() -> dict:
    config = RetrievalConfig.from_env()
    store = UserProfileStore(config)
    store.create_collection(drop_if_exists=True)

    logger.info("Generating user profiles from Postgres metadata...")
    profiles = generate_profiles(MetadataRepository().list_artifacts())
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
    parser = argparse.ArgumentParser(description="Index user profiles into Qdrant")
    parser.parse_args()

    result = run_profile_indexing()
    print(f"\nDone — inserted: {result['inserted']}, total users: {result['total']}")


if __name__ == "__main__":
    main()
