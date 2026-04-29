"""Milvus collection for user workspace profiles."""

import logging
from typing import Dict, List, Optional

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from .config import RetrievalConfig

logger = logging.getLogger(__name__)

COLLECTION_NAME = "user_profiles"


class UserProfileStore:
    """Manages the user_profiles Milvus collection."""

    def __init__(self, config: RetrievalConfig):
        self.config = config
        self.collection: Optional[Collection] = None
        self._loaded = False
        self._connect()

    def _connect(self):
        connections.connect("default", host=self.config.milvus_host, port=str(self.config.milvus_port))
        logger.info(f"Connected to Milvus at {self.config.milvus_host}:{self.config.milvus_port}")

    def _schema(self) -> CollectionSchema:
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=255, is_primary=True, auto_id=False),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="user_profile", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.config.embedding_dimension),
            FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=1000),
        ]
        return CollectionSchema(fields, description="User workspace profiles")

    def create_collection(self, drop_if_exists: bool = False):
        if utility.has_collection(COLLECTION_NAME):
            if drop_if_exists:
                utility.drop_collection(COLLECTION_NAME)
                logger.info(f"Dropped existing collection: {COLLECTION_NAME}")
            else:
                self.collection = Collection(COLLECTION_NAME)
                return

        self.collection = Collection(COLLECTION_NAME, schema=self._schema())
        self.collection.create_index(
            "vector",
            {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 8, "efConstruction": 64}},
        )
        logger.info(f"Created collection: {COLLECTION_NAME}")

    def _ensure_loaded(self):
        if not self._loaded and self.collection:
            self.collection.load()
            self._loaded = True

    def upsert_profiles(self, profiles: List[Dict]) -> int:
        if not self.collection:
            raise RuntimeError("Collection not initialized — call create_collection() first")

        self._ensure_loaded()
        for p in profiles:
            try:
                self.collection.delete(f'user_id == "{p["user_id"]}"')
            except Exception:
                pass

        data = [
            [p["id"] for p in profiles],
            [p["user_id"] for p in profiles],
            [p["user_profile"][:500] for p in profiles],
            [p["vector"] for p in profiles],
            [p["tags"][:1000] for p in profiles],
        ]
        result = self.collection.insert(data)
        self.collection.flush()
        self._loaded = False
        logger.info(f"Upserted {len(result.primary_keys)} user profiles")
        return len(result.primary_keys)

    def get_all_profiles(self) -> List[Dict]:
        if not self.collection:
            return []
        try:
            self._ensure_loaded()
            rows = self.collection.query(
                expr='user_id != ""',
                output_fields=["id", "user_id", "user_profile", "tags"],
                limit=1000,
            )
            return rows
        except Exception as e:
            logger.error(f"Failed to query all profiles: {e}")
            return []

    def get_profile(self, user_id: str) -> Optional[Dict]:
        if not self.collection:
            return None
        try:
            self._ensure_loaded()
            rows = self.collection.query(
                expr=f'user_id == "{user_id}"',
                output_fields=["id", "user_id", "user_profile", "tags"],
                limit=1,
            )
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Failed to get profile for {user_id}: {e}")
            return None

    def count(self) -> int:
        if not self.collection:
            return 0
        try:
            self._ensure_loaded()
            return self.collection.num_entities
        except Exception:
            return 0
