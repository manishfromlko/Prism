"""Milvus collection for platform documentation chunks."""

import logging
from typing import Dict, List, Optional

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from ..config import RetrievalConfig

logger = logging.getLogger(__name__)

COLLECTION_NAME = "platform_docs"


class DocumentChunkStore:
    """Manages the platform_docs Milvus collection."""

    def __init__(self, config: RetrievalConfig):
        self.config = config
        self.collection: Optional[Collection] = None
        self._loaded = False
        self._connect()

    def _connect(self):
        connections.connect("default", uri=f"http://{self.config.milvus_host}:{self.config.milvus_port}")

    def _schema(self) -> CollectionSchema:
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.config.embedding_dimension),
        ]
        return CollectionSchema(fields, description="Platform documentation chunks for chatbot QA")

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

    def upsert_chunks(self, chunks: List[Dict]) -> int:
        if not self.collection:
            raise RuntimeError("Collection not initialized — call create_collection() first")
        if not chunks:
            return 0

        self._ensure_loaded()
        # Delete by doc_id before reinserting (handles re-ingestion)
        doc_ids = list({c["doc_id"] for c in chunks})
        for doc_id in doc_ids:
            try:
                self.collection.delete(f'doc_id == "{doc_id}"')
            except Exception:
                pass

        data = [
            [c["doc_id"] for c in chunks],
            [c["chunk_id"] for c in chunks],
            [c["chunk_text"][:4000] for c in chunks],
            [c["source_file"] for c in chunks],
            [c["vector"] for c in chunks],
        ]
        result = self.collection.insert(data)
        self.collection.flush()
        self._loaded = False
        logger.info(f"Upserted {len(result.primary_keys)} document chunks")
        return len(result.primary_keys)

    def similarity_search(self, vector: List[float], top_k: int = 5) -> List[Dict]:
        if not self.collection:
            return []
        try:
            self._ensure_loaded()
            results = self.collection.search(
                data=[vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=top_k,
                output_fields=["doc_id", "chunk_id", "chunk_text", "source_file"],
            )
            hits = []
            for hit in results[0]:
                hits.append({
                    "doc_id": hit.entity.get("doc_id"),
                    "chunk_id": hit.entity.get("chunk_id"),
                    "chunk_text": hit.entity.get("chunk_text"),
                    "source_file": hit.entity.get("source_file"),
                    "score": hit.score,
                })
            return hits
        except Exception as e:
            logger.error(f"Doc similarity search failed: {e}")
            return []

    def count(self) -> int:
        if not self.collection:
            return 0
        try:
            self._ensure_loaded()
            return self.collection.num_entities
        except Exception:
            return 0
