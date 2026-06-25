"""Unit tests for embedding service."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.retrieval.config import RetrievalConfig
from src.retrieval.embeddings import EmbeddingService


class TestEmbeddingService:
    """Test cases for EmbeddingService."""

    @patch("src.retrieval.embeddings.make_openai_client")
    def test_initialization(self, mock_make_client):
        """Test service initialization."""
        mock_client = MagicMock()
        mock_make_client.return_value = mock_client

        config = RetrievalConfig()
        service = EmbeddingService(config)

        mock_make_client.assert_called_once_with()
        assert service.client == mock_client
        assert service.config == config

    @patch("src.retrieval.embeddings.make_openai_client")
    def test_generate_embedding(self, mock_make_client):
        """Test single embedding generation."""
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
        )
        mock_make_client.return_value = mock_client

        config = RetrievalConfig()
        service = EmbeddingService(config)

        result = service.generate_embedding("test text")

        mock_client.embeddings.create.assert_called_once_with(
            input=["test text"],
            model=config.embedding_model,
        )
        assert result == [0.1, 0.2, 0.3]

    @patch("src.retrieval.embeddings.make_openai_client")
    def test_generate_embeddings_batch(self, mock_make_client):
        """Test batch embedding generation."""
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[0.1, 0.2]),
                SimpleNamespace(embedding=[0.3, 0.4]),
            ]
        )
        mock_make_client.return_value = mock_client

        config = RetrievalConfig()
        service = EmbeddingService(config)

        texts = ["text1", "text2"]
        result = service.generate_embeddings(texts)

        mock_client.embeddings.create.assert_called_once_with(
            input=texts,
            model=config.embedding_model,
        )
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    @patch("src.retrieval.embeddings.make_openai_client")
    def test_get_dimension(self, mock_make_client):
        """Test getting embedding dimension."""
        mock_make_client.return_value = MagicMock()
        config = RetrievalConfig(embedding_dimension=512)
        service = EmbeddingService(config)

        assert service.get_dimension() == 512

    @patch("src.retrieval.embeddings.make_openai_client")
    def test_is_loaded(self, mock_make_client):
        """Test model loaded status."""
        mock_client = MagicMock()
        mock_make_client.return_value = mock_client

        config = RetrievalConfig()
        service = EmbeddingService(config)

        assert service.is_loaded() is True

        service.client = None
        assert service.is_loaded() is False

    @patch("src.retrieval.embeddings.make_openai_client")
    def test_generate_embedding_uses_cache(self, mock_make_client):
        """Test embedding cache avoids duplicate OpenAI calls."""
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
        )
        mock_make_client.return_value = mock_client

        config = RetrievalConfig()
        service = EmbeddingService(config)

        assert service.generate_embedding("test") == [0.1, 0.2, 0.3]
        assert service.generate_embedding("test") == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()

    @patch("src.retrieval.embeddings.make_openai_client")
    def test_generate_embeddings_uses_cached_items(self, mock_make_client):
        """Test batch generation only requests uncached texts."""
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = [
            SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])]),
            SimpleNamespace(data=[SimpleNamespace(embedding=[0.3, 0.4])]),
        ]
        mock_make_client.return_value = mock_client

        config = RetrievalConfig()
        service = EmbeddingService(config)

        assert service.generate_embedding("text1") == [0.1, 0.2]
        assert service.generate_embeddings(["text1", "text2"]) == [[0.1, 0.2], [0.3, 0.4]]

        mock_client.embeddings.create.assert_called_with(
            input=["text2"],
            model=config.embedding_model,
        )
