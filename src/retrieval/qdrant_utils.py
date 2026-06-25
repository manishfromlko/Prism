"""Shared Qdrant helpers for retrieval stores."""

import uuid
from typing import Any, Dict, Iterable, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .config import RetrievalConfig


def make_client(config: RetrievalConfig) -> QdrantClient:
    return QdrantClient(
        host=config.qdrant_host,
        port=config.qdrant_port,
        api_key=config.qdrant_api_key,
        https=False,
        check_compatibility=False,
    )


def distance_for_metric(metric: str) -> models.Distance:
    normalized = metric.upper()
    if normalized in {"IP", "DOT"}:
        return models.Distance.DOT
    if normalized in {"L2", "EUCLID", "EUCLIDEAN"}:
        return models.Distance.EUCLID
    return models.Distance.COSINE


def ensure_collection(
    client: QdrantClient,
    name: str,
    vector_size: int,
    distance: models.Distance = models.Distance.COSINE,
    drop_if_exists: bool = False,
) -> None:
    exists = client.collection_exists(name)
    if exists and drop_if_exists:
        client.delete_collection(name)
        exists = False

    if not exists:
        client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(size=vector_size, distance=distance),
        )


def stable_point_id(collection_name: str, key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection_name}:{key}"))


def field_filter(**matches: Any) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
            for key, value in matches.items()
        ]
    )


def any_filter(key: str, values: Iterable[Any]) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key=key,
                match=models.MatchAny(any=list(values)),
            )
        ]
    )


def scroll_payloads(
    client: QdrantClient,
    collection_name: str,
    scroll_filter: Optional[models.Filter] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = None
    while len(rows) < limit:
        points, offset = client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=min(1000, limit - len(rows)),
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            rows.append({"id": point.id, **(point.payload or {})})
        if offset is None:
            break
    return rows
