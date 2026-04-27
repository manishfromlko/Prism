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

        assert config.milvus_host == "localhost"
        assert config.milvus_port == 19530
        assert config.collection_name == "kubeflow_artifacts"
        assert config.embedding_model == "all-MiniLM-L6-v2"
        assert config.embedding_dimension == 384
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.batch_size == 32
        assert config.similarity_metric == "COSINE"
        assert config.default_top_k == 10
        assert config.index_type == "HNSW"

    def test_from_env(self):
        """Test configuration from environment variables."""
        env_vars = {
            "MILVUS_HOST": "milvus.example.com",
            "MILVUS_PORT": "9091",
            "MILVUS_COLLECTION": "test_collection",
            "EMBEDDING_MODEL": "all-mpnet-base-v2",
            "CHUNK_SIZE": "500",
            "CHUNK_OVERLAP": "100",
            "BATCH_SIZE": "16",
        }

        with patch.dict(os.environ, env_vars):
            config = RetrievalConfig.from_env()

            assert config.milvus_host == "milvus.example.com"
            assert config.milvus_port == 9091
            assert config.collection_name == "test_collection"
            assert config.embedding_model == "all-mpnet-base-v2"
            assert config.chunk_size == 500
            assert config.chunk_overlap == 100
            assert config.batch_size == 16

    def test_from_env_defaults(self):
        """Test from_env with no environment variables set."""
        with patch.dict(os.environ, {}, clear=True):
            config = RetrievalConfig.from_env()

            assert config.milvus_host == "localhost"
            assert config.milvus_port == 19530
            assert config.collection_name == "kubeflow_artifacts"