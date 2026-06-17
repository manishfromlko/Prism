"""Qdrant collection management for artifact-level summaries."""

import logging
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .config import RetrievalConfig
from .qdrant_utils import ensure_collection, field_filter, make_client, scroll_payloads, stable_point_id

logger = logging.getLogger(__name__)

COLLECTION_NAME = "artifact_summaries"


class ArtifactSummaryStore:
    """Manages the artifact_summaries Qdrant collection."""

    def __init__(self, config: RetrievalConfig):
        self.config = config
        self.client: Optional[QdrantClient] = None
        self.collection: Optional[str] = None
        self._connect()

    def _connect(self):
        self.client = make_client(self.config)
        logger.info(f"Connected to Qdrant at {self.config.qdrant_host}:{self.config.qdrant_port}")

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

    def upsert_summaries(self, summaries: List[Dict]) -> int:
        if not self.collection:
            raise RuntimeError("Collection not initialized - call create_collection() first")
        if not summaries:
            return 0

        points = [
            models.PointStruct(
                id=stable_point_id(COLLECTION_NAME, s["artifact_id"]),
                vector=s["vector"],
                payload={
                    "user_id": s["user_id"],
                    "artifact_id": s["artifact_id"],
                    "artifact_summary": s["artifact_summary"][:1500],
                    "tags": s["tags"][:1000],
                },
            )
            for s in summaries
        ]
        self._ensure_client().upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
        logger.info(f"Upserted {len(points)} artifact summaries")
        return len(points)

    def get_all_summaries(self, limit: int = 10000) -> List[Dict]:
        if not self.collection:
            return []
        try:
            return scroll_payloads(self._ensure_client(), COLLECTION_NAME, limit=limit)
        except Exception as e:
            logger.error(f"Failed to query all artifact summaries: {e}")
            return []

    def get_workspace_summaries(self, user_id: str, limit: int = 1000) -> List[Dict]:
        if not self.collection:
            return []
        try:
            return scroll_payloads(
                self._ensure_client(),
                COLLECTION_NAME,
                scroll_filter=field_filter(user_id=user_id),
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Failed to query summaries for workspace {user_id}: {e}")
            return []

    def get_summary(self, user_id: str, artifact_id: str) -> Optional[Dict]:
        if not self.collection:
            return None
        try:
            rows = scroll_payloads(
                self._ensure_client(),
                COLLECTION_NAME,
                scroll_filter=field_filter(user_id=user_id, artifact_id=artifact_id),
                limit=1,
            )
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Failed to get summary for {user_id}/{artifact_id}: {e}")
            return None

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
            return [
                {
                    "user_id": (hit.payload or {}).get("user_id"),
                    "artifact_id": (hit.payload or {}).get("artifact_id"),
                    "artifact_summary": (hit.payload or {}).get("artifact_summary"),
                    "tags": (hit.payload or {}).get("tags", ""),
                    "score": hit.score,
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Artifact similarity search failed: {e}")
            return []
