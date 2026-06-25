"""Qdrant vector store integration for storing and retrieving embeddings."""

import json
import logging
from typing import Any, Dict, List, Optional, Set

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .config import RetrievalConfig
from .qdrant_utils import distance_for_metric, ensure_collection, make_client, stable_point_id

logger = logging.getLogger(__name__)


class VectorStore:
    """Qdrant-based vector store for artifact embeddings."""

    def __init__(self, config: RetrievalConfig):
        self.config = config
        self.client: Optional[QdrantClient] = None
        self.collection: Optional[str] = None
        self._connect()

    def _connect(self) -> None:
        try:
            logger.info(
                "Connecting to Qdrant at %s:%s",
                self.config.qdrant_host,
                self.config.qdrant_port,
            )
            self.client = make_client(self.config)
            logger.info("Connected to Qdrant successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def _ensure_client(self) -> QdrantClient:
        if not self.client:
            raise RuntimeError("Qdrant client not initialized")
        return self.client

    def _ensure_collection(self) -> str:
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        return self.collection

    def create_collection(self, drop_if_exists: bool = False) -> None:
        client = self._ensure_client()
        ensure_collection(
            client=client,
            name=self.config.collection_name,
            vector_size=self.config.embedding_dimension,
            distance=distance_for_metric(self.config.similarity_metric),
            drop_if_exists=drop_if_exists,
        )
        self.collection = self.config.collection_name

    def drop_collection(self) -> None:
        client = self._ensure_client()
        if client.collection_exists(self.config.collection_name):
            client.delete_collection(self.config.collection_name)
        self.collection = None

    def insert_vectors(
        self,
        artifact_ids: List[str],
        vectors: List[List[float]],
        contents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> List[str]:
        collection = self._ensure_collection()
        client = self._ensure_client()

        points = []
        for offset, (artifact_id, vector, content, metadata) in enumerate(
            zip(artifact_ids, vectors, contents, metadatas)
        ):
            point_id = stable_point_id(collection, f"artifact:{artifact_id}:{offset}")
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "artifact_id": artifact_id,
                        "content": content,
                        "metadata": metadata,
                    },
                )
            )

        client.upsert(collection_name=collection, points=points, wait=True)
        logger.info(f"Upserted {len(points)} vectors into Qdrant")
        return [str(point.id) for point in points]

    def _build_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[models.Filter]:
        if not filters:
            return None
        conditions = []
        for key, value in filters.items():
            payload_key = key if key in {"artifact_id", "content"} else f"metadata.{key}"
            conditions.append(
                models.FieldCondition(key=payload_key, match=models.MatchValue(value=value))
            )
        return models.Filter(must=conditions)

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        collection = self._ensure_collection()
        response = self._ensure_client().query_points(
            collection_name=collection,
            query=query_vector,
            query_filter=self._build_filter(filters),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        results = getattr(response, "points", response)

        formatted_results = []
        for hit in results:
            payload = hit.payload or {}
            formatted_results.append(
                {
                    "artifact_id": payload.get("artifact_id"),
                    "content": payload.get("content"),
                    "metadata": payload.get("metadata") or {},
                    "score": hit.score,
                    "id": hit.id,
                }
            )
        return formatted_results

    def get_collection_stats(self) -> Dict[str, Any]:
        collection = self._ensure_collection()
        client = self._ensure_client()
        info = client.get_collection(collection)
        count = client.count(collection_name=collection, exact=True).count
        return {
            "name": collection,
            "num_entities": count,
            "schema": str(info.config.params.vectors),
        }

    def list_artifact_ids(self, batch_size: int = 1000) -> Set[str]:
        collection = self._ensure_collection()
        client = self._ensure_client()
        ids: Set[str] = set()
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=collection,
                limit=batch_size,
                offset=offset,
                with_payload=["artifact_id"],
                with_vectors=False,
            )
            ids.update(
                str(point.payload.get("artifact_id"))
                for point in points
                if point.payload and point.payload.get("artifact_id")
            )
            if offset is None:
                break
        return ids

    def update_vectors(
        self,
        artifact_ids: List[str],
        vectors: List[List[float]],
        contents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> int:
        self.delete_vectors(artifact_ids)
        return len(self.insert_vectors(artifact_ids, vectors, contents, metadatas))

    def delete_vectors(self, artifact_ids: List[str]) -> int:
        collection = self._ensure_collection()
        client = self._ensure_client()
        if not artifact_ids:
            return 0

        selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="artifact_id",
                        match=models.MatchAny(any=artifact_ids),
                    )
                ]
            )
        )
        result = client.count(
            collection_name=collection,
            count_filter=selector.filter,
            exact=True,
        )
        client.delete(collection_name=collection, points_selector=selector, wait=True)
        return result.count

    def get_vector_count(self) -> int:
        return self.get_collection_stats()["num_entities"]

    def backup_collection(self, backup_path: str) -> None:
        collection = self._ensure_collection()
        client = self._ensure_client()
        rows = []
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=collection,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            for point in points:
                payload = point.payload or {}
                rows.append(
                    {
                        "artifact_id": payload.get("artifact_id"),
                        "vector": point.vector,
                        "content": payload.get("content"),
                        "metadata": payload.get("metadata") or {},
                    }
                )
            if offset is None:
                break

        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)

    def restore_collection(self, backup_path: str) -> int:
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return len(
            self.insert_vectors(
                [item["artifact_id"] for item in data],
                [item["vector"] for item in data],
                [item["content"] for item in data],
                [item["metadata"] for item in data],
            )
        )

    def optimize_index(self) -> None:
        self._ensure_collection()
        logger.info("Qdrant manages the vector index automatically")

    def get_index_info(self) -> Dict[str, Any]:
        collection = self._ensure_collection()
        info = self._ensure_client().get_collection(collection)
        return {
            "index_type": "HNSW",
            "metric_type": self.config.similarity_metric,
            "params": str(info.config.params.vectors),
        }
