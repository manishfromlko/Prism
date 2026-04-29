"""Unit tests for embedding service."""

from unittest.mock import MagicMock, patch

import pytest

from src.retrieval.config import RetrievalConfig
from src.retrieval.embeddings import EmbeddingService


class TestEmbeddingService:
    """Test cases for EmbeddingService."""

    @patch('src.retrieval.embeddings.SentenceTransformer')
    def test_initialization(self, mock_transformer):
        """Test service initialization."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        config = RetrievalConfig()
        service = EmbeddingService(config)

        mock_transformer.assert_called_once_with(config.embedding_model)
        assert service.model == mock_model
        assert service.config == config

    @patch('src.retrieval.embeddings.SentenceTransformer')
    def test_generate_embedding(self, mock_transformer):
        """Test single embedding generation."""
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1, 0.2, 0.3]  # Mock numpy array
        mock_transformer.return_value = mock_model

        config = RetrievalConfig()
        service = EmbeddingService(config)

        result = service.generate_embedding("test text")

        mock_model.encode.assert_called_once_with("test text", convert_to_numpy=True)
        assert result == [0.1, 0.2, 0.3]

    @patch('src.retrieval.embeddings.SentenceTransformer')
    def test_generate_embeddings_batch(self, mock_transformer):
        """Test batch embedding generation."""
        mock_model = MagicMock()
        mock_model.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]  # Mock numpy array
        mock_transformer.return_value = mock_model

        config = RetrievalConfig()
        service = EmbeddingService(config)

        texts = ["text1", "text2"]
        result = service.generate_embeddings(texts)

        mock_model.encode.assert_called_once_with(
            texts,
            batch_size=config.batch_size,
            convert_to_numpy=True
        )
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_get_dimension(self):
        """Test getting embedding dimension."""
        config = RetrievalConfig(embedding_dimension=512)
        service = EmbeddingService(config)

        assert service.get_dimension() == 512

    @patch('src.retrieval.embeddings.SentenceTransformer')
    def test_is_loaded(self, mock_transformer):
        """Test model loaded status."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        config = RetrievalConfig()
        service = EmbeddingService(config)

        assert service.is_loaded() is True

        # Test with failed loading
        service.model = None
        assert service.is_loaded() is False

    @patch('src.retrieval.embeddings.SentenceTransformer')
    def test_generate_embedding_no_model(self, mock_transformer):
        """Test embedding generation without loaded model."""
        mock_transformer.side_effect = Exception("Load failed")

        config = RetrievalConfig()
        service = EmbeddingService(config)

        # Manually set model to None to simulate failure
        service.model = None

        with pytest.raises(RuntimeError, match="Embedding model not loaded"):
            service.generate_embedding("test")

    @patch('src.retrieval.embeddings.SentenceTransformer')
    def test_generate_embeddings_no_model(self, mock_transformer):
        """Test batch embedding generation without loaded model."""
        mock_transformer.side_effect = Exception("Load failed")

        config = RetrievalConfig()
        service = EmbeddingService(config)

        # Manually set model to None to simulate failure
        service.model = None

        with pytest.raises(RuntimeError, match="Embedding model not loaded"):
            service.generate_embeddings(["test"])