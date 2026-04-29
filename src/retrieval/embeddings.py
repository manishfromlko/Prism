"""Embedding service for generating vector representations of text."""

import hashlib
import logging
import time
from typing import Dict, List, Optional, Tuple

from sentence_transformers import SentenceTransformer

from .config import RetrievalConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using sentence transformers."""

    def __init__(self, config: RetrievalConfig):
        """Initialize the embedding service.

        Args:
            config: Retrieval configuration
        """
        self.config = config
        self.model: Optional[SentenceTransformer] = None
        self._cache: Dict[str, List[float]] = {}
        self._load_model()

    def _load_model(self) -> None:
        """Load the sentence transformer model."""
        try:
            logger.info(f"Loading embedding model: {self.config.embedding_model}")
            self.model = SentenceTransformer(self.config.embedding_model)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def generate_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed
            use_cache: Whether to use caching

        Returns:
            List of float values representing the embedding vector
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")

        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                return self._cache[cache_key]

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            result = embedding.tolist()

            if use_cache:
                self._cache[cache_key] = result

            return result
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def generate_embeddings(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of input texts to embed
            use_cache: Whether to use caching

        Returns:
            List of embedding vectors
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")

        # Check cache for each text
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)

        if use_cache:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    results[i] = self._cache[cache_key]
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))

        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                logger.info(f"Generating embeddings for {len(uncached_texts)} texts")
                start_time = time.time()

                embeddings = self.model.encode(uncached_texts, batch_size=self.config.batch_size, convert_to_numpy=True)
                embedding_list = embeddings.tolist()

                end_time = time.time()
                logger.info(f"Generated {len(embedding_list)} embeddings in {end_time - start_time:.2f}s")

                # Store in cache and results
                for i, (idx, embedding) in enumerate(zip(uncached_indices, embedding_list)):
                    results[idx] = embedding
                    if use_cache:
                        cache_key = self._get_cache_key(uncached_texts[i])
                        self._cache[cache_key] = embedding

            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
                raise

        return results

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text.

        Args:
            text: Input text

        Returns:
            Cache key string
        """
        # Use hash of text + model name for cache key
        content = f"{self.config.embedding_model}:{text}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get_dimension(self) -> int:
        """Get the dimension of the embedding vectors.

        Returns:
            Embedding dimension
        """
        return self.config.embedding_dimension

    def is_loaded(self) -> bool:
        """Check if the model is loaded.

        Returns:
            True if model is loaded, False otherwise
        """
        return self.model is not None

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "cached_embeddings": len(self._cache),
            "cache_memory_mb": self._estimate_cache_memory(),
        }

    def _estimate_cache_memory(self) -> float:
        """Estimate memory usage of cache in MB.

        Returns:
            Estimated memory in MB
        """
        # Rough estimate: each embedding is ~dimension * 4 bytes (float32)
        bytes_per_embedding = self.config.embedding_dimension * 4
        total_bytes = len(self._cache) * bytes_per_embedding
        return total_bytes / (1024 * 1024)

    def validate_embeddings(self, texts: List[str], embeddings: List[List[float]]) -> Dict[str, float]:
        """Validate embedding quality and compute metrics.

        Args:
            texts: Original texts
            embeddings: Generated embeddings

        Returns:
            Dictionary with validation metrics
        """
        if len(texts) != len(embeddings):
            raise ValueError("Texts and embeddings count mismatch")

        metrics = {
            "count": len(embeddings),
            "avg_dimension": sum(len(emb) for emb in embeddings) / len(embeddings),
            "min_dimension": min(len(emb) for emb in embeddings),
            "max_dimension": max(len(emb) for emb in embeddings),
        }

        # Check for zero vectors (potential issues)
        zero_vectors = sum(1 for emb in embeddings if all(x == 0 for x in emb))
        metrics["zero_vectors"] = zero_vectors

        # Check dimension consistency
        expected_dim = self.config.embedding_dimension
        correct_dim = sum(1 for emb in embeddings if len(emb) == expected_dim)
        metrics["correct_dimension_ratio"] = correct_dim / len(embeddings)

        return metrics

    def switch_model(self, model_name: str) -> None:
        """Switch to a different embedding model.

        Args:
            model_name: Name of the new model to load
        """
        if model_name == self.config.embedding_model and self.model:
            logger.info(f"Model {model_name} already loaded")
            return

        logger.info(f"Switching to model: {model_name}")
        self.config.embedding_model = model_name
        self.model = None  # Force reload
        self.clear_cache()  # Clear cache as embeddings will be different
        self._load_model()