"""Unit tests for the Qdrant vector store."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval.config import RetrievalConfig
from src.retrieval.vector_store import VectorStore


class TestVectorStore:
    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_initialization(self, mock_client_class):
        config = RetrievalConfig()
        store = VectorStore(config)

        mock_client_class.assert_called_once_with(
            host=config.qdrant_host,
            port=config.qdrant_port,
            api_key=config.qdrant_api_key,
        )
        assert store.config == config
        assert store.collection is None

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_create_collection_new(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = False
        mock_client_class.return_value = mock_client

        config = RetrievalConfig()
        store = VectorStore(config)
        store.create_collection()

        mock_client.collection_exists.assert_called_with(config.collection_name)
        mock_client.create_collection.assert_called_once()
        assert store.collection == config.collection_name

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_create_collection_existing(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True
        mock_client_class.return_value = mock_client

        config = RetrievalConfig()
        store = VectorStore(config)
        store.create_collection()

        mock_client.create_collection.assert_not_called()
        assert store.collection == config.collection_name

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_create_collection_drop_existing(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True
        mock_client_class.return_value = mock_client

        config = RetrievalConfig()
        store = VectorStore(config)
        store.create_collection(drop_if_exists=True)

        mock_client.delete_collection.assert_called_once_with(config.collection_name)
        mock_client.create_collection.assert_called_once()

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_insert_vectors(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = RetrievalConfig()
        store = VectorStore(config)
        store.collection = config.collection_name

        result = store.insert_vectors(
            ["art1", "art2", "art3"],
            [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
            ["content1", "content2", "content3"],
            [{"key": "val1"}, {"key": "val2"}, {"key": "val3"}],
        )

        mock_client.upsert.assert_called_once()
        kwargs = mock_client.upsert.call_args.kwargs
        assert kwargs["collection_name"] == config.collection_name
        assert kwargs["wait"] is True
        assert len(kwargs["points"]) == 3
        assert len(result) == 3

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_insert_vectors_no_collection(self, mock_client_class):
        config = RetrievalConfig()
        store = VectorStore(config)

        with pytest.raises(RuntimeError, match="Collection not initialized"):
            store.insert_vectors([], [], [], [])

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_search_vectors(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.query_points.return_value = SimpleNamespace(
            points=[
                SimpleNamespace(
                    id="point-1",
                    score=0.95,
                    payload={
                        "artifact_id": "art1",
                        "content": "content1",
                        "metadata": {"key": "val"},
                    },
                )
            ]
        )
        mock_client_class.return_value = mock_client

        config = RetrievalConfig()
        store = VectorStore(config)
        store.collection = config.collection_name

        results = store.search_vectors([0.1, 0.2], top_k=5)

        mock_client.query_points.assert_called_once()
        assert len(results) == 1
        assert results[0]["artifact_id"] == "art1"
        assert results[0]["score"] == 0.95

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_search_vectors_no_collection(self, mock_client_class):
        config = RetrievalConfig()
        store = VectorStore(config)

        with pytest.raises(RuntimeError, match="Collection not initialized"):
            store.search_vectors([0.1, 0.2])

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_get_collection_stats(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.get_collection.return_value = SimpleNamespace(
            config=SimpleNamespace(params=SimpleNamespace(vectors="vector-config"))
        )
        mock_client.count.return_value = SimpleNamespace(count=100)
        mock_client_class.return_value = mock_client

        config = RetrievalConfig()
        store = VectorStore(config)
        store.collection = config.collection_name

        stats = store.get_collection_stats()

        assert stats["name"] == config.collection_name
        assert stats["num_entities"] == 100
        assert "schema" in stats

    @patch("src.retrieval.qdrant_utils.QdrantClient")
    def test_drop_collection(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True
        mock_client_class.return_value = mock_client

        config = RetrievalConfig()
        store = VectorStore(config)
        store.collection = config.collection_name
        store.drop_collection()

        mock_client.delete_collection.assert_called_once_with(config.collection_name)
        assert store.collection is None
