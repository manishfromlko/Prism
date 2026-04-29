"""Milvus collection management for artifact-level summaries."""

import logging
from typing import Dict, List, Optional

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from .config import RetrievalConfig

logger = logging.getLogger(__name__)

COLLECTION_NAME = "artifact_summaries"


class ArtifactSummaryStore:
    """Manages the artifact_summaries Milvus collection."""

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
            FieldSchema(name="artifact_id", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="artifact_summary", dtype=DataType.VARCHAR, max_length=1500),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.config.embedding_dimension),
            FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=1000),
        ]
        return CollectionSchema(fields, description="Artifact-level summaries and tags")

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

    def upsert_summaries(self, summaries: List[Dict]) -> int:
        if not self.collection:
            raise RuntimeError("Collection not initialized - call create_collection() first")
        if not summaries:
            return 0

        self._ensure_loaded()
        for s in summaries:
            try:
                self.collection.delete(f'id == "{s["id"]}"')
            except Exception:
                pass

        data = [
            [s["id"] for s in summaries],
            [s["user_id"] for s in summaries],
            [s["artifact_id"] for s in summaries],
            [s["artifact_summary"][:1500] for s in summaries],
            [s["vector"] for s in summaries],
            [s["tags"][:1000] for s in summaries],
        ]
        result = self.collection.insert(data)
        self.collection.flush()
        self._loaded = False
        logger.info(f"Upserted {len(result.primary_keys)} artifact summaries")
        return len(result.primary_keys)

    def get_all_summaries(self, limit: int = 10000) -> List[Dict]:
        if not self.collection:
            return []
        try:
            self._ensure_loaded()
            return self.collection.query(
                expr='user_id != ""',
                output_fields=["id", "user_id", "artifact_id", "artifact_summary", "tags"],
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Failed to query all artifact summaries: {e}")
            return []

    def get_workspace_summaries(self, user_id: str, limit: int = 1000) -> List[Dict]:
        if not self.collection:
            return []
        try:
            self._ensure_loaded()
            return self.collection.query(
                expr=f'user_id == "{user_id}"',
                output_fields=["id", "user_id", "artifact_id", "artifact_summary", "tags"],
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Failed to query summaries for workspace {user_id}: {e}")
            return []

    def get_summary(self, user_id: str, artifact_id: str) -> Optional[Dict]:
        if not self.collection:
            return None
        try:
            self._ensure_loaded()
            summary_id = f"artifact:{user_id}:{artifact_id}"
            rows = self.collection.query(
                expr=f'id == "{summary_id}"',
                output_fields=["id", "user_id", "artifact_id", "artifact_summary", "tags"],
                limit=1,
            )
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Failed to get summary for {user_id}/{artifact_id}: {e}")
            return None
