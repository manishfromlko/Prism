"""
Indexer: reads the ingestion catalog and populates Milvus with embeddings.

Run after ingestion to bring the vector store in sync with the catalog:

    python -m src.retrieval.indexer --catalog dataset/.ingestion/ingestion_catalog.json

Modes:
    incremental (default) — only indexes artifact_ids not already in Milvus
    full                  — drops and recreates the collection, then indexes everything
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Set

from .config import RetrievalConfig
from .document_loader import DocumentLoader
from .embeddings import EmbeddingService
from .vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _get_indexed_ids(store: VectorStore) -> Set[str]:
    """Return the set of artifact_ids already present in Milvus."""
    try:
        store.collection.load()
        # Paginate in chunks of 16 384 (Milvus per-query max)
        ids: Set[str] = set()
        offset = 0
        chunk = 16_384
        while True:
            rows = store.collection.query(
                expr='artifact_id != ""',
                output_fields=["artifact_id"],
                limit=chunk,
                offset=offset,
            )
            if not rows:
                break
            ids.update(r["artifact_id"] for r in rows)
            if len(rows) < chunk:
                break
            offset += chunk
        return ids
    except Exception as e:
        logger.warning(f"Could not query existing artifact IDs: {e}")
        return set()


def run_indexing(catalog_path: str, mode: str = "incremental") -> Dict:
    """
    Index catalog artifacts into Milvus.

    Returns a summary dict: {inserted, skipped, errors, total}.
    """
    config = RetrievalConfig.from_env()

    store = VectorStore(config)

    if mode == "full":
        logger.info("Full mode: dropping and recreating collection")
        store.create_collection(drop_if_exists=True)
        already_indexed: Set[str] = set()
    else:
        store.create_collection(drop_if_exists=False)
        logger.info("Incremental mode: querying existing artifact IDs from Milvus")
        already_indexed = _get_indexed_ids(store)
        logger.info(f"Already indexed: {len(already_indexed)} artifacts")

    loader = DocumentLoader(catalog_path, config)
    all_docs = loader.load_documents()
    logger.info(f"Catalog contains {len(all_docs)} indexable documents")

    if mode == "incremental":
        new_docs = [d for d in all_docs if d.metadata.get("artifact_id") not in already_indexed]
    else:
        new_docs = all_docs

    skipped = len(all_docs) - len(new_docs)
    logger.info(f"To index: {len(new_docs)} new | skipping: {skipped} already present")

    if not new_docs:
        return {"inserted": 0, "skipped": skipped, "errors": 0, "total": len(all_docs)}

    embedder = EmbeddingService(config)
    texts = [doc.page_content for doc in new_docs]
    logger.info(f"Generating embeddings for {len(texts)} documents...")
    embeddings = embedder.generate_embeddings(texts)

    artifact_ids = [doc.metadata.get("artifact_id", "") for doc in new_docs]
    contents = [doc.page_content[:5000] for doc in new_docs]
    metadatas = [doc.metadata for doc in new_docs]

    logger.info("Inserting vectors into Milvus...")
    store.insert_vectors(artifact_ids, embeddings, contents, metadatas)

    result = {
        "inserted": len(new_docs),
        "skipped": skipped,
        "errors": 0,
        "total": len(all_docs),
    }
    logger.info(
        f"Indexing complete — inserted: {result['inserted']}, "
        f"skipped: {result['skipped']}, total: {result['total']}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index ingestion catalog artifacts into Milvus"
    )
    parser.add_argument(
        "--catalog",
        default=os.getenv("INGESTION_CATALOG_PATH", "dataset/.ingestion/ingestion_catalog.json"),
        help="Path to ingestion_catalog.json",
    )
    parser.add_argument(
        "--mode",
        choices=["incremental", "full"],
        default="incremental",
        help="incremental (default): only new artifacts | full: drop + reindex everything",
    )
    args = parser.parse_args()

    if not os.path.exists(args.catalog):
        print(f"ERROR: catalog not found: {args.catalog}", file=sys.stderr)
        sys.exit(1)

    result = run_indexing(args.catalog, args.mode)
    print(
        f"\nDone — inserted: {result['inserted']}, "
        f"skipped: {result['skipped']}, "
        f"total: {result['total']}"
    )


if __name__ == "__main__":
    main()
