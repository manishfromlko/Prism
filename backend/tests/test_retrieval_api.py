"""Tests for retrieval API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from .api import app, create_app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock all services for testing."""
    with patch('src.retrieval.api.config') as mock_config, \
         patch('src.retrieval.api.vector_store') as mock_vector_store, \
         patch('src.retrieval.api.embedding_service') as mock_embedding, \
         patch('src.retrieval.api.query_processor') as mock_processor, \
         patch('src.retrieval.api.profiler') as mock_profiler:

        # Configure mocks
        mock_config.embedding_model = "test-model"
        mock_vector_store.get_collection_stats.return_value = {"num_entities": 100}
        mock_embedding.is_loaded.return_value = True
        mock_embedding.get_cache_stats.return_value = {
            "cached_embeddings": 50,
            "cache_memory_mb": 25.5
        }

        yield {
            'config': mock_config,
            'vector_store': mock_vector_store,
            'embedding': mock_embedding,
            'processor': mock_processor,
            'profiler': mock_profiler
        }


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_healthy(self, client, mock_services):
        """Test health check when all services are healthy."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["vector_store"]["connected"] is True
        assert data["embedding_service"]["model_loaded"] is True

    def test_health_degraded(self, client, mock_services):
        """Test health check when some services are down."""
        mock_services['vector_store'].get_collection_stats.side_effect = Exception("Connection failed")

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["vector_store"]["connected"] is False

    def test_health_unhealthy(self, client, mock_services):
        """Test health check when all services are down."""
        mock_services['vector_store'].get_collection_stats.side_effect = Exception("Connection failed")
        mock_services['embedding'].is_loaded.return_value = False

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "unhealthy"


class TestQueryEndpoint:
    """Test query endpoint."""

    def test_query_success(self, client, mock_services):
        """Test successful query execution."""
        # Mock retriever
        mock_retriever = Mock()
        mock_doc = Mock()
        mock_doc.page_content = "test content"
        mock_doc.metadata = {"artifact_id": "test_123", "score": 0.95}
        mock_retriever._get_relevant_documents.return_value = [mock_doc]

        with patch('src.retrieval.api.VectorRetriever', return_value=mock_retriever):
            response = client.post("/query", json={
                "query": "test query",
                "top_k": 5
            })

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test query"
        assert len(data["results"]) == 1
        assert data["results"][0]["artifact_id"] == "test_123"

    def test_query_hybrid_search(self, client, mock_services):
        """Test hybrid search query."""
        mock_retriever = Mock()
        mock_retriever._get_relevant_documents.return_value = []

        with patch('src.retrieval.api.HybridRetriever', return_value=mock_retriever):
            response = client.post("/query", json={
                "query": "test query",
                "use_hybrid": True
            })

        assert response.status_code == 200

    def test_query_service_unavailable(self, client):
        """Test query when services are not initialized."""
        with patch('src.retrieval.api.vector_store', None):
            response = client.post("/query", json={"query": "test"})

        assert response.status_code == 503

    def test_query_invalid_request(self, client, mock_services):
        """Test query with invalid request data."""
        response = client.post("/query", json={"invalid": "data"})
        assert response.status_code == 422  # Validation error


class TestProfileEndpoint:
    """Test workspace profile endpoint."""

    def test_profile_success(self, client, mock_services):
        """Test successful profile retrieval."""
        mock_profile_data = {
            "workspace_id": "test_workspace",
            "artifact_count": 10,
            "top_tools": [{"tool": "pandas", "count": 5}],
            "top_topics": [{"topic": "Machine Learning", "relevance": 0.8}],
            "collaboration_patterns": {"notebooks": 3},
            "last_updated": "2024-01-01T00:00:00Z",
            "file_types": {"python": 7, "notebook": 3},
            "code_metrics": {"total_lines": 1000}
        }

        mock_services['profiler'].profile_workspace.return_value = mock_profile_data

        response = client.get("/profile/workspace/test_workspace")
        assert response.status_code == 200

        data = response.json()
        assert data["workspace_id"] == "test_workspace"
        assert data["artifact_count"] == 10

    def test_profile_not_found(self, client, mock_services):
        """Test profile for non-existent workspace."""
        mock_services['profiler'].profile_workspace.return_value = {
            "workspace_id": "nonexistent",
            "artifact_count": 0,
            "top_tools": [],
            "top_topics": [],
            "collaboration_patterns": {},
            "last_updated": None,
            "file_types": {},
            "code_metrics": {}
        }

        response = client.get("/profile/workspace/nonexistent")
        assert response.status_code == 200

        data = response.json()
        assert data["artifact_count"] == 0


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics_success(self, client, mock_services):
        """Test successful metrics retrieval."""
        response = client.get("/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "uptime_seconds" in data
        assert "total_queries" in data
        assert "avg_query_time_ms" in data
        assert "error_rate" in data
        assert "memory_usage_mb" in data


class TestSyncEndpoint:
    """Test sync endpoint."""

    def test_sync_success(self, client, mock_services):
        """Test successful sync operation."""
        response = client.post("/admin/sync")
        assert response.status_code == 200

        data = response.json()
        assert "sync_id" in data
        assert "status" in data
        assert "processed_count" in data


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_internal_server_error(self, client, mock_services):
        """Test internal server error handling."""
        mock_services['vector_store'].get_collection_stats.side_effect = Exception("Unexpected error")

        response = client.get("/health")
        # Health endpoint should handle errors gracefully
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "unhealthy"