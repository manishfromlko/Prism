"""FastAPI application for vector retrieval and profiling."""

import logging
import time
from typing import Dict, List, Optional, Any
import psutil

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import RetrievalConfig
from .retriever import VectorRetriever, HybridRetriever, QueryProcessor
from .vector_store import VectorStore
from .embeddings import EmbeddingService
from .profiling import WorkspaceProfiler

logger = logging.getLogger(__name__)

# Metrics tracking
START_TIME = time.time()
QUERY_COUNT = 0
TOTAL_QUERY_TIME = 0.0
ERROR_COUNT = 0

# Pydantic models
class QueryRequest(BaseModel):
    """Request model for vector queries."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(10, description="Number of results to return", ge=1, le=100)
    workspace_ids: Optional[List[str]] = Field(None, description="Limit search to specific workspaces")
    use_hybrid: bool = Field(False, description="Use hybrid search (vector + keyword)")

class QueryResponse(BaseModel):
    """Response model for query results."""
    results: List[Dict] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total matching artifacts")
    query_time_ms: float = Field(..., description="Search execution time in milliseconds")
    query: str = Field(..., description="Original query")

class WorkspaceProfile(BaseModel):
    """Response model for workspace profiling."""
    workspace_id: str
    artifact_count: int
    top_tools: List[Dict[str, Any]]
    top_topics: List[Dict[str, Any]]
    collaboration_patterns: Dict[str, Any]
    last_updated: Optional[str]

class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str = Field(..., description="System health status")
    vector_store: Dict[str, Any] = Field(..., description="Vector store status")
    embedding_service: Dict[str, Any] = Field(..., description="Embedding service status")
    cache_stats: Dict[str, Any] = Field(..., description="Cache statistics")

class SyncRequest(BaseModel):
    """Request model for data synchronization."""
    force_full: bool = Field(False, description="Force full reprocessing")

class MetricsResponse(BaseModel):
    """Response model for system metrics."""
    uptime_seconds: float
    total_queries: int
    avg_query_time_ms: float
    error_rate: float
    memory_usage_mb: float

class LogResponse(BaseModel):
    """Response model for recent logs."""
    logs: List[Dict[str, Any]]
    total_count: int

# Global services (initialized on startup)
config: Optional[RetrievalConfig] = None
vector_store: Optional[VectorStore] = None
embedding_service: Optional[EmbeddingService] = None
query_processor: Optional[QueryProcessor] = None
profiler: Optional[WorkspaceProfiler] = None

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Kubeflow Workspace Retrieval API",
        description="Vector-based search and profiling for Kubeflow workspaces",
        version="1.0.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app

app = create_app()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global config, vector_store, embedding_service, query_processor, profiler

    try:
        config = RetrievalConfig.from_env()
        vector_store = VectorStore(config)
        embedding_service = EmbeddingService(config)
        query_processor = QueryProcessor(config)
        profiler = WorkspaceProfiler(config, config.ingestion_catalog_path)

        # Create collection if it doesn't exist
        vector_store.create_collection()

        logger.info("API services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get system performance metrics."""
    global QUERY_COUNT, TOTAL_QUERY_TIME, ERROR_COUNT, START_TIME

    try:
        uptime = time.time() - START_TIME
        avg_query_time = TOTAL_QUERY_TIME / QUERY_COUNT if QUERY_COUNT > 0 else 0
        error_rate = ERROR_COUNT / (QUERY_COUNT + ERROR_COUNT) if (QUERY_COUNT + ERROR_COUNT) > 0 else 0

        # Get memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        return MetricsResponse(
            uptime_seconds=uptime,
            total_queries=QUERY_COUNT,
            avg_query_time_ms=avg_query_time,
            error_rate=error_rate,
            memory_usage_mb=memory_mb
        )

    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics retrieval failed")

@app.get("/health", response_model=HealthResponse)
async def get_health():
    """Check system health and status."""
    try:
        vector_status = {"connected": False, "collection_count": 0, "total_vectors": 0}
        if vector_store:
            try:
                stats = vector_store.get_collection_stats()
                vector_status = {
                    "connected": True,
                    "collection_count": 1,
                    "total_vectors": stats.get("num_entities", 0)
                }
            except Exception:
                vector_status["connected"] = False

        embedding_status = {"model_loaded": False, "model_name": None}
        if embedding_service:
            embedding_status = {
                "model_loaded": embedding_service.is_loaded(),
                "model_name": config.embedding_model if config else None
            }

        cache_stats = {"cached_embeddings": 0, "cache_memory_mb": 0}
        if embedding_service:
            cache_stats = embedding_service.get_cache_stats()

        if vector_status["connected"] and embedding_status["model_loaded"]:
            status = "healthy"
        elif vector_status["connected"] or embedding_status["model_loaded"]:
            status = "degraded"
        else:
            status = "unhealthy"

        return HealthResponse(
            status=status,
            vector_store=vector_status,
            embedding_service=embedding_status,
            cache_stats=cache_stats
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Perform vector similarity search."""
    import time
    global QUERY_COUNT, TOTAL_QUERY_TIME, ERROR_COUNT

    if not vector_store or not config:
        ERROR_COUNT += 1
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        start_time = time.time()

        # Create retriever
        if request.use_hybrid:
            retriever = HybridRetriever(vector_store=vector_store, config=config)
        else:
            retriever = VectorRetriever(vector_store=vector_store, config=config)

        # Perform search
        documents = retriever._get_relevant_documents(
            request.query,
            run_manager=None,
            top_k=request.top_k
        )

        # Format results
        results = []
        for doc in documents:
            results.append({
                "artifact_id": doc.metadata.get("artifact_id"),
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": doc.metadata.get("score", 0.0)
            })

        query_time = (time.time() - start_time) * 1000

        # Update metrics
        QUERY_COUNT += 1
        TOTAL_QUERY_TIME += query_time

        return QueryResponse(
            results=results,
            total_found=len(results),
            query_time_ms=query_time,
            query=request.query
        )

    except Exception as e:
        ERROR_COUNT += 1
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Query execution failed")

@app.get("/profile/workspace/{workspace_id}", response_model=WorkspaceProfile)
async def get_workspace_profile(workspace_id: str):
    """Get profiling insights for a workspace."""
    if not profiler:
        raise HTTPException(status_code=503, detail="Profiler not initialized")

    try:
        profile_data = profiler.profile_workspace(workspace_id)

        # Convert to response model
        return WorkspaceProfile(**profile_data)

    except Exception as e:
        logger.error(f"Profile retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Profile retrieval failed")

@app.post("/admin/sync", response_model=SyncResponse)
async def sync_data(request: SyncRequest):
    """Synchronize with latest ingestion catalog."""
    # This would trigger reprocessing of the ingestion catalog
    # For now, return a placeholder response

    try:
        return SyncResponse(
            sync_id="sync_001",
            status="completed",
            processed_count=0,
            errors=[]
        )

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail="Sync operation failed")

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Kubeflow Workspace Retrieval API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)