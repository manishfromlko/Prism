"""Unit tests for retrieval configuration."""

import os
from unittest.mock import patch

import pytest

from src.retrieval.config import RetrievalConfig


class TestRetrievalConfig:
    """Test cases for RetrievalConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetrievalConfig()

        assert config.qdrant_host == "127.0.0.1"
        assert config.qdrant_port == 6333
        assert config.collection_name == "kubeflow_artifacts"
        assert config.embedding_model == "text-embedding-3-small"
        assert config.embedding_dimension == 1536
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.batch_size == 32
        assert config.similarity_metric == "COSINE"
        assert config.default_top_k == 10
        assert config.index_type == "HNSW"

    def test_from_env(self):
        """Test configuration from environment variables."""
        env_vars = {
            "QDRANT_HOST": "qdrant.example.com",
            "QDRANT_PORT": "6334",
            "QDRANT_COLLECTION": "test_collection",
            "EMBEDDING_MODEL": "all-mpnet-base-v2",
            "CHUNK_SIZE": "500",
            "CHUNK_OVERLAP": "100",
            "BATCH_SIZE": "16",
        }

        with patch.dict(os.environ, env_vars):
            config = RetrievalConfig.from_env()

            assert config.qdrant_host == "qdrant.example.com"
            assert config.qdrant_port == 6334
            assert config.collection_name == "test_collection"
            assert config.embedding_model == "all-mpnet-base-v2"
            assert config.chunk_size == 500
            assert config.chunk_overlap == 100
            assert config.batch_size == 16

    def test_from_env_defaults(self):
        """Test from_env with no environment variables set."""
        with patch.dict(os.environ, {}, clear=True):
            config = RetrievalConfig.from_env()

            assert config.qdrant_host == "127.0.0.1"
            assert config.qdrant_port == 6333
            assert config.collection_name == "kubeflow_artifacts"
