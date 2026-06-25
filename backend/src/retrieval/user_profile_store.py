"""Qdrant collection for user workspace profiles."""

import logging
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .config import RetrievalConfig
from .qdrant_utils import ensure_collection, field_filter, make_client, scroll_payloads, stable_point_id

logger = logging.getLogger(__name__)

COLLECTION_NAME = "user_profiles"


class UserProfileStore:
    """Manages the user_profiles Qdrant collection."""

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

    def upsert_profiles(self, profiles: List[Dict]) -> int:
        if not self.collection:
            raise RuntimeError("Collection not initialized - call create_collection() first")
        if not profiles:
            return 0

        points = [
            models.PointStruct(
                id=stable_point_id(COLLECTION_NAME, p["user_id"]),
                vector=p["vector"],
                payload={
                    "user_id": p["user_id"],
                    "user_profile": p["user_profile"][:500],
                    "tags": p["tags"][:1000],
                },
            )
            for p in profiles
        ]
        self._ensure_client().upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
        logger.info(f"Upserted {len(points)} user profiles")
        return len(points)

    def delete_profiles(self, user_ids: List[str]) -> int:
        """Delete profiles for users that no longer have summaries."""
        if not self.collection or not user_ids:
            return 0

        point_ids = [
            stable_point_id(COLLECTION_NAME, user_id)
            for user_id in user_ids
        ]
        self._ensure_client().delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.PointIdsList(points=point_ids),
            wait=True,
        )
        logger.info(f"Deleted {len(point_ids)} user profiles")
        return len(point_ids)

    def get_all_profiles(self) -> List[Dict]:
        if not self.collection:
            return []
        try:
            return scroll_payloads(self._ensure_client(), COLLECTION_NAME, limit=1000)
        except Exception as e:
            logger.error(f"Failed to query all profiles: {e}")
            return []

    def get_all_user_ids(self) -> List[str]:
        return [r["user_id"] for r in self.get_all_profiles() if r.get("user_id")]

    def get_profile(self, user_id: str) -> Optional[Dict]:
        if not self.collection:
            return None
        try:
            rows = scroll_payloads(
                self._ensure_client(),
                COLLECTION_NAME,
                scroll_filter=field_filter(user_id=user_id),
                limit=1,
            )
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Failed to get profile for {user_id}: {e}")
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
                    "user_profile": (hit.payload or {}).get("user_profile"),
                    "tags": (hit.payload or {}).get("tags", ""),
                    "score": hit.score,
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"User similarity search failed: {e}")
            return []

    def count(self) -> int:
        if not self.collection:
            return 0
        try:
            return self._ensure_client().count(collection_name=COLLECTION_NAME, exact=True).count
        except Exception:
            return 0
