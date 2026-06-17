"""Qdrant collection for platform documentation chunks."""

import logging
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from ..config import RetrievalConfig
from ..qdrant_utils import any_filter, ensure_collection, make_client, stable_point_id

logger = logging.getLogger(__name__)

COLLECTION_NAME = "platform_docs"


class DocumentChunkStore:
    """Manages the platform_docs Qdrant collection."""

    def __init__(self, config: RetrievalConfig):
        self.config = config
        self.client: Optional[QdrantClient] = None
        self.collection: Optional[str] = None
        self._connect()

    def _connect(self):
        self.client = make_client(self.config)

    def _ensure_client(self) -> QdrantClient:
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        return self.client

    def _ensure_loaded(self):
        self.collection = COLLECTION_NAME

    def create_collection(self, drop_if_exists: bool = False):
        ensure_collection(
            self._ensure_client(),
            COLLECTION_NAME,
            self.config.embedding_dimension,
            drop_if_exists=drop_if_exists,
        )
        self.collection = COLLECTION_NAME

    def upsert_chunks(self, chunks: List[Dict]) -> int:
        if not self.collection:
            raise RuntimeError("Collection not initialized - call create_collection() first")
        if not chunks:
            return 0

        doc_ids = list({c["doc_id"] for c in chunks})
        self._ensure_client().delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(filter=any_filter("doc_id", doc_ids)),
            wait=True,
        )

        points = [
            models.PointStruct(
                id=stable_point_id(COLLECTION_NAME, c["chunk_id"]),
                vector=c["vector"],
                payload={
                    "doc_id": c["doc_id"],
                    "chunk_id": c["chunk_id"],
                    "chunk_text": c["chunk_text"][:4000],
                    "source_file": c["source_file"],
                },
            )
            for c in chunks
        ]
        self._ensure_client().upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
        logger.info(f"Upserted {len(points)} document chunks")
        return len(points)

    def similarity_search(self, vector: List[float], top_k: int = 5) -> List[Dict]:
        if not self.collection:
            return []
        try:
            response = self._ensure_client().query_points(
                collection_name=COLLECTION_NAME,
                query=vector,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
            results = getattr(response, "points", response)
            hits = []
            for hit in results:
                payload = hit.payload or {}
                hits.append(
                    {
                        "doc_id": payload.get("doc_id"),
                        "chunk_id": payload.get("chunk_id"),
                        "chunk_text": payload.get("chunk_text"),
                        "source_file": payload.get("source_file"),
                        "score": hit.score,
                    }
                )
            return hits
        except Exception as e:
            logger.error(f"Doc similarity search failed: {e}")
            return []

    def count(self) -> int:
        if not self.collection:
            return 0
        try:
            return self._ensure_client().count(collection_name=COLLECTION_NAME, exact=True).count
        except Exception:
            return 0
