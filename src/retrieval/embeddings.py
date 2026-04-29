"""Embedding service — OpenAI text-embedding-3-small."""

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config import RetrievalConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates text embeddings via the OpenAI Embeddings API."""

    def __init__(self, config: RetrievalConfig):
        self.config = config
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. "
                "Add it to the .env file at the project root."
            )
        self.client = OpenAI(api_key=api_key)
        self._cache: Dict[str, List[float]] = {}
        logger.info(f"EmbeddingService ready (model={config.embedding_model})")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # text-embedding-3-small limit: 8 192 tokens. CSV/numeric content can be
    # 1-2 chars/token, so 4 000 chars guarantees we stay under the limit for
    # any content type while still capturing the most semantically useful text.
    _MAX_CHARS = 4_000

    def _truncate(self, text: str) -> str:
        return text[: self._MAX_CHARS] if len(text) > self._MAX_CHARS else text

    def generate_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """Embed a single text string."""
        text = self._truncate(text)
        if use_cache:
            key = self._cache_key(text)
            if key in self._cache:
                return self._cache[key]

        response = self.client.embeddings.create(
            input=[text],
            model=self.config.embedding_model,
        )
        embedding: List[float] = response.data[0].embedding

        if use_cache:
            self._cache[self._cache_key(text)] = embedding
        return embedding

    def generate_embeddings(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """Embed a list of texts, batching requests and using the cache."""
        texts = [self._truncate(t) for t in texts]
        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_texts: List[str] = []
        uncached_indices: List[int] = []

        if use_cache:
            for i, text in enumerate(texts):
                key = self._cache_key(text)
                if key in self._cache:
                    results[i] = self._cache[key]
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = list(texts)
            uncached_indices = list(range(len(texts)))

        if uncached_texts:
            logger.info(
                f"Requesting {len(uncached_texts)} embeddings from OpenAI "
                f"(model={self.config.embedding_model})"
            )
            # OpenAI supports up to 2 048 inputs per call; we batch conservatively
            batch_size = self.config.batch_size
            for start in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[start : start + batch_size]
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.config.embedding_model,
                )
                for j, item in enumerate(response.data):
                    global_idx = uncached_indices[start + j]
                    results[global_idx] = item.embedding
                    if use_cache:
                        self._cache[self._cache_key(batch[j])] = item.embedding

                logger.info(
                    f"  batch {start // batch_size + 1}/"
                    f"{-(-len(uncached_texts) // batch_size)}: "
                    f"{len(batch)} embeddings received"
                )

        return results  # type: ignore[return-value]

    def get_dimension(self) -> int:
        return self.config.embedding_dimension

    def is_loaded(self) -> bool:
        """Always True — the model is remote."""
        return self.client is not None

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        bytes_per_embedding = self.config.embedding_dimension * 4  # float32
        return {
            "cached_embeddings": len(self._cache),
            "cache_memory_mb": round(len(self._cache) * bytes_per_embedding / (1024 * 1024), 3),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cache_key(self, text: str) -> str:
        content = f"{self.config.embedding_model}:{text}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()
