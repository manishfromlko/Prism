"""Unit tests for vector store."""

from unittest.mock import MagicMock, patch

import pytest

from src.retrieval.config import RetrievalConfig
from src.retrieval.vector_store import VectorStore


class TestVectorStore:
    """Test cases for VectorStore."""

    @patch('src.retrieval.vector_store.connections')
    def test_initialization(self, mock_connections):
        """Test vector store initialization."""
        config = RetrievalConfig()
        store = VectorStore(config)

        mock_connections.connect.assert_called_once_with(
            alias="default",
            host=config.milvus_host,
            port=config.milvus_port
        )
        assert store.config == config
        assert store.collection is None

    @patch('src.retrieval.vector_store.connections')
    @patch('src.retrieval.vector_store.utility')
    @patch('src.retrieval.vector_store.Collection')
    def test_create_collection_new(self, mock_collection, mock_utility, mock_connections):
        """Test creating a new collection."""
        mock_utility.has_collection.return_value = False
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        config = RetrievalConfig()
        store = VectorStore(config)
        store.create_collection()

        mock_utility.has_collection.assert_called_with(config.collection_name)
        mock_collection.assert_called_once()
        mock_coll_instance.create_index.assert_called_once()
        assert store.collection == mock_coll_instance

    @patch('src.retrieval.vector_store.connections')
    @patch('src.retrieval.vector_store.utility')
    @patch('src.retrieval.vector_store.Collection')
    def test_create_collection_existing(self, mock_collection, mock_utility, mock_connections):
        """Test using existing collection."""
        mock_utility.has_collection.return_value = True
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        config = RetrievalConfig()
        store = VectorStore(config)
        store.create_collection()

        mock_utility.has_collection.assert_called_with(config.collection_name)
        mock_collection.assert_called_once_with(
            name=config.collection_name,
            using="default"
        )
        mock_coll_instance.create_index.assert_not_called()
        assert store.collection == mock_coll_instance

    @patch('src.retrieval.vector_store.connections')
    @patch('src.retrieval.vector_store.utility')
    @patch('src.retrieval.vector_store.Collection')
    def test_create_collection_drop_existing(self, mock_collection, mock_utility, mock_connections):
        """Test dropping existing collection."""
        mock_utility.has_collection.return_value = True
        mock_coll_instance = MagicMock()
        mock_collection.return_value = mock_coll_instance

        config = RetrievalConfig()
        store = VectorStore(config)
        store.create_collection(drop_if_exists=True)

        mock_utility.drop_collection.assert_called_once_with(config.collection_name)
        mock_collection.assert_called_once()

    @patch('src.retrieval.vector_store.connections')
    def test_insert_vectors(self, mock_connections):
        """Test inserting vectors."""
        config = RetrievalConfig()
        store = VectorStore(config)

        # Mock collection
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.primary_keys = [1, 2, 3]
        mock_collection.insert.return_value = mock_result
        store.collection = mock_collection

        artifact_ids = ["art1", "art2", "art3"]
        vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        contents = ["content1", "content2", "content3"]
        metadatas = [{"key": "val1"}, {"key": "val2"}, {"key": "val3"}]

        result = store.insert_vectors(artifact_ids, vectors, contents, metadatas)

        mock_collection.insert.assert_called_once_with([
            artifact_ids, vectors, contents, metadatas
        ])
        mock_collection.flush.assert_called_once()
        assert result == [1, 2, 3]

    @patch('src.retrieval.vector_store.connections')
    def test_insert_vectors_no_collection(self, mock_connections):
        """Test inserting vectors without collection."""
        config = RetrievalConfig()
        store = VectorStore(config)
        store.collection = None

        with pytest.raises(RuntimeError, match="Collection not initialized"):
            store.insert_vectors([], [], [], [])

    @patch('src.retrieval.vector_store.connections')
    def test_search_vectors(self, mock_connections):
        """Test vector search."""
        config = RetrievalConfig()
        store = VectorStore(config)

        # Mock collection and search results
        mock_collection = MagicMock()
        store.collection = mock_collection

        mock_hit = MagicMock()
        mock_hit.id = 1
        mock_hit.score = 0.95
        mock_hit.entity = {
            "artifact_id": "art1",
            "content": "content1",
            "metadata": {"key": "val"}
        }

        mock_hits = MagicMock()
        mock_hits.__iter__ = lambda self: iter([mock_hit])
        mock_results = [mock_hits]
        mock_collection.search.return_value = mock_results

        query_vector = [0.1, 0.2]
        results = store.search_vectors(query_vector, top_k=5)

        mock_collection.load.assert_called_once()
        mock_collection.search.assert_called_once()
        assert len(results) == 1
        assert results[0]["artifact_id"] == "art1"
        assert results[0]["score"] == 0.95

    @patch('src.retrieval.vector_store.connections')
    def test_search_vectors_no_collection(self, mock_connections):
        """Test search without collection."""
        config = RetrievalConfig()
        store = VectorStore(config)
        store.collection = None

        with pytest.raises(RuntimeError, match="Collection not initialized"):
            store.search_vectors([0.1, 0.2])

    @patch('src.retrieval.vector_store.connections')
    def test_get_collection_stats(self, mock_connections):
        """Test getting collection statistics."""
        config = RetrievalConfig()
        store = VectorStore(config)

        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collection.num_entities = 100
        mock_collection.schema = "test_schema"
        store.collection = mock_collection

        stats = store.get_collection_stats()

        assert stats["name"] == "test_collection"
        assert stats["num_entities"] == 100
        assert "schema" in stats

    @patch('src.retrieval.vector_store.connections')
    @patch('src.retrieval.vector_store.utility')
    def test_drop_collection(self, mock_utility, mock_connections):
        """Test dropping collection."""
        config = RetrievalConfig()
        store = VectorStore(config)

        mock_utility.has_collection.return_value = True

        store.drop_collection()

        mock_utility.drop_collection.assert_called_once_with(config.collection_name)
        assert store.collection is None