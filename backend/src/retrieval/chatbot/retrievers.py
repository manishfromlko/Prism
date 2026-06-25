"""Retrieval functions — one per source, fully independent."""

import logging
from typing import Dict, List

from ..artifact_summary_store import ArtifactSummaryStore
from ..embeddings import EmbeddingService
from ..user_profile_store import UserProfileStore
from .doc_store import DocumentChunkStore

logger = logging.getLogger(__name__)


class DocRetriever:
    """Retrieves chunks from the platform_docs collection."""

    def __init__(self, doc_store: DocumentChunkStore, embedding_service: EmbeddingService):
        self.store = doc_store
        self.embedder = embedding_service

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self.store.collection:
            logger.warning("platform_docs collection not loaded")
            return []
        vector = self.embedder.generate_embedding(query)
        return self.store.similarity_search(vector, top_k=top_k)


class ArtifactRetriever:
    """Retrieves from artifact_summaries using vector similarity."""

    def __init__(self, artifact_store: ArtifactSummaryStore, embedding_service: EmbeddingService):
        self.store = artifact_store
        self.embedder = embedding_service

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self.store.collection:
            logger.warning("artifact_summaries collection not loaded")
            return []
        try:
            self.store._ensure_loaded()
            vector = self.embedder.generate_embedding(query)
            results = self.store.collection.search(
                data=[vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=top_k,
                output_fields=["user_id", "artifact_id", "artifact_summary", "tags"],
            )
            hits = []
            for hit in results[0]:
                hits.append({
                    "user_id": hit.entity.get("user_id"),
                    "artifact_id": hit.entity.get("artifact_id"),
                    "artifact_summary": hit.entity.get("artifact_summary"),
                    "tags": hit.entity.get("tags", ""),
                    "score": hit.score,
                })
            return hits
        except Exception as e:
            logger.error(f"Artifact retrieval failed: {e}")
            return []


class UserRetriever:
    """Retrieves from user_profiles using vector similarity."""

    def __init__(self, user_store: UserProfileStore, embedding_service: EmbeddingService):
        self.store = user_store
        self.embedder = embedding_service

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self.store.collection:
            logger.warning("user_profiles collection not loaded")
            return []
        try:
            self.store._ensure_loaded()
            vector = self.embedder.generate_embedding(query)
            results = self.store.collection.search(
                data=[vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=top_k,
                output_fields=["user_id", "user_profile", "tags"],
            )
            hits = []
            for hit in results[0]:
                hits.append({
                    "user_id": hit.entity.get("user_id"),
                    "user_profile": hit.entity.get("user_profile"),
                    "tags": hit.entity.get("tags", ""),
                    "score": hit.score,
                })
            return hits
        except Exception as e:
            logger.error(f"User retrieval failed: {e}")
            return []
