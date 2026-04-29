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
from .indexer import run_indexing

logger = logging.getLogger(__name__)

START_TIME = time.time()
QUERY_COUNT = 0
TOTAL_QUERY_TIME = 0.0
ERROR_COUNT = 0

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    top_k: int = Field(10, description="Number of results to return", ge=1, le=100)
    workspace_ids: Optional[List[str]] = Field(None, description="Limit search to specific workspaces")
    use_hybrid: bool = Field(False, description="Use hybrid search (vector + keyword)")

class QueryResponse(BaseModel):
    results: List[Dict] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total matching artifacts")
    query_time_ms: float = Field(..., description="Search execution time in milliseconds")
    query: str = Field(..., description="Original query")

class WorkspaceProfile(BaseModel):
    workspace_id: str
    artifact_count: int
    top_tools: List[Dict[str, Any]]
    top_topics: List[Dict[str, Any]]
    collaboration_patterns: Dict[str, Any]
    last_updated: Optional[str]
    file_types: Dict[str, Any] = Field(default_factory=dict)
    code_metrics: Dict[str, Any] = Field(default_factory=dict)
    recent_artifacts: List[Dict[str, Any]] = Field(default_factory=list)

class HealthResponse(BaseModel):
    status: str
    vector_store: Dict[str, Any]
    embedding_service: Dict[str, Any]
    cache_stats: Dict[str, Any]

class SyncRequest(BaseModel):
    force_full: bool = Field(False, description="Force full reprocessing")

class SyncResponse(BaseModel):
    sync_id: str
    status: str
    processed_count: int
    errors: List[str]

class MetricsResponse(BaseModel):
    uptime_seconds: float
    total_queries: int
    avg_query_time_ms: float
    error_rate: float
    memory_usage_mb: float

# ---------------------------------------------------------------------------
# Global services
# ---------------------------------------------------------------------------

config: Optional[RetrievalConfig] = None
vector_store: Optional[VectorStore] = None
embedding_service: Optional[EmbeddingService] = None
query_processor: Optional[QueryProcessor] = None
profiler: Optional[WorkspaceProfiler] = None

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="Kubeflow Workspace Retrieval API",
        description="Vector-based search and profiling for Kubeflow workspaces",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

app = create_app()

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    global config, vector_store, embedding_service, query_processor, profiler
    try:
        config = RetrievalConfig.from_env()
        vector_store = VectorStore(config)
        embedding_service = EmbeddingService(config)
        query_processor = QueryProcessor(config)
        profiler = WorkspaceProfiler(config, config.ingestion_catalog_path)
        vector_store.create_collection()

        # Pre-load collection into Milvus memory so the first search is not slow
        if vector_store.collection:
            vector_store.collection.load()
            vector_store._collection_loaded = True

        # Pre-warm the catalog cache so workspace/profile endpoints are instant.
        # Non-fatal: if the catalog path is wrong the server still starts and
        # search (/query) continues to work; only workspace/profile endpoints 503.
        try:
            profiler.loader.load_catalog()
        except FileNotFoundError:
            logger.warning(
                f"Catalog not found at '{config.ingestion_catalog_path}'. "
                "Workspace and profile endpoints will return 503 until the catalog "
                "is available. Set INGESTION_CATALOG_PATH to fix this."
            )

        logger.info("API services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "Kubeflow Workspace Retrieval API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health", response_model=HealthResponse)
async def get_health():
    try:
        vector_status: Dict[str, Any] = {"connected": False, "collection_count": 0, "total_vectors": 0}
        if vector_store:
            try:
                stats = vector_store.get_collection_stats()
                vector_status = {
                    "connected": True,
                    "collection_count": 1,
                    "total_vectors": stats.get("num_entities", 0),
                }
            except Exception:
                vector_status["connected"] = False

        embedding_status: Dict[str, Any] = {"model_loaded": False, "model_name": None}
        if embedding_service:
            embedding_status = {
                "model_loaded": embedding_service.is_loaded(),
                "model_name": config.embedding_model if config else None,
            }

        cache_stats: Dict[str, Any] = {"cached_embeddings": 0, "cache_memory_mb": 0}
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
            cache_stats=cache_stats,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    global QUERY_COUNT, TOTAL_QUERY_TIME, ERROR_COUNT, START_TIME
    try:
        uptime = time.time() - START_TIME
        avg_query_time = TOTAL_QUERY_TIME / QUERY_COUNT if QUERY_COUNT > 0 else 0
        error_rate = ERROR_COUNT / (QUERY_COUNT + ERROR_COUNT) if (QUERY_COUNT + ERROR_COUNT) > 0 else 0
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        return MetricsResponse(
            uptime_seconds=uptime,
            total_queries=QUERY_COUNT,
            avg_query_time_ms=avg_query_time,
            error_rate=error_rate,
            memory_usage_mb=memory_mb,
        )
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics retrieval failed")

# ---------------------------------------------------------------------------
# Workspace endpoints
# ---------------------------------------------------------------------------

@app.get("/workspaces")
async def list_workspaces():
    """List all workspaces from the ingestion catalog."""
    if not profiler:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        catalog = profiler.loader.load_catalog()
        workspaces_raw = catalog.get('workspaces', {})
        artifacts = catalog.get('artifacts', {})

        # Count ingested artifacts per workspace
        artifact_counts: Dict[str, int] = {}
        for art in artifacts.values():
            ws_id = art.get('workspace_id', '')
            artifact_counts[ws_id] = artifact_counts.get(ws_id, 0) + 1

        status_map = {'success': 'active', 'failed': 'error', 'running': 'active'}
        data = []
        for ws_id, ws in workspaces_raw.items():
            data.append({
                'id': ws_id,
                'name': ws_id,
                'description': ws.get('notes') or f"Workspace owned by {ws.get('owner', ws_id)}",
                'artifact_count': artifact_counts.get(ws_id, ws.get('file_count', 0)),
                'last_updated': ws.get('last_ingested_at', ''),
                'created_at': ws.get('last_ingested_at', ''),
                'status': status_map.get(ws.get('status', 'success'), 'active'),
                'owner': ws.get('owner', ''),
            })

        return {
            'data': data,
            'pagination': {
                'page': 1,
                'page_size': len(data),
                'total_count': len(data),
                'total_pages': 1,
                'has_next': False,
                'has_previous': False,
            },
        }
    except Exception as e:
        logger.error(f"Failed to list workspaces: {e}")
        raise HTTPException(status_code=500, detail="Failed to list workspaces")

@app.get("/workspaces/{workspace_id}")
async def get_workspace_by_id(workspace_id: str):
    """Get a single workspace from the ingestion catalog."""
    if not profiler:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        catalog = profiler.loader.load_catalog()
        workspaces_raw = catalog.get('workspaces', {})
        ws = workspaces_raw.get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")

        artifacts = catalog.get('artifacts', {})
        artifact_count = sum(1 for a in artifacts.values() if a.get('workspace_id') == workspace_id)

        status_map = {'success': 'active', 'failed': 'error', 'running': 'active'}
        return {
            'data': {
                'id': workspace_id,
                'name': workspace_id,
                'description': ws.get('notes') or f"Workspace owned by {ws.get('owner', workspace_id)}",
                'artifact_count': artifact_count,
                'last_updated': ws.get('last_ingested_at', ''),
                'created_at': ws.get('last_ingested_at', ''),
                'status': status_map.get(ws.get('status', 'success'), 'active'),
                'owner': ws.get('owner', ''),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get workspace")

# ---------------------------------------------------------------------------
# Profile endpoint
# ---------------------------------------------------------------------------

@app.get("/profile/workspace/{workspace_id}")
async def get_workspace_profile(workspace_id: str):
    """Get profiling insights for a workspace."""
    if not profiler:
        raise HTTPException(status_code=503, detail="Profiler not initialized")
    try:
        return profiler.profile_workspace(workspace_id)
    except Exception as e:
        logger.error(f"Profile retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Profile retrieval failed")

# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Perform vector similarity search."""
    global QUERY_COUNT, TOTAL_QUERY_TIME, ERROR_COUNT

    if not vector_store or not config:
        ERROR_COUNT += 1
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        start_time = time.time()

        if request.use_hybrid:
            retriever = HybridRetriever(
                vector_store=vector_store,
                config=config,
                embedding_service=embedding_service,
            )
        else:
            retriever = VectorRetriever(
                vector_store=vector_store,
                config=config,
                embedding_service=embedding_service,
            )

        documents = retriever._get_relevant_documents(
            request.query, run_manager=None, top_k=request.top_k
        )

        results = []
        for doc in documents:
            results.append({
                "artifact_id": doc.metadata.get("artifact_id"),
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": doc.metadata.get("score", 0.0),
            })

        query_time = (time.time() - start_time) * 1000
        QUERY_COUNT += 1
        TOTAL_QUERY_TIME += query_time

        return QueryResponse(
            results=results,
            total_found=len(results),
            query_time_ms=query_time,
            query=request.query,
        )
    except Exception as e:
        ERROR_COUNT += 1
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Query execution failed")

# ---------------------------------------------------------------------------
# Admin endpoint
# ---------------------------------------------------------------------------

@app.post("/admin/sync", response_model=SyncResponse)
async def sync_data(request: SyncRequest):
    """Re-index the ingestion catalog into Milvus (incremental or full)."""
    if not config:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        import uuid
        from concurrent.futures import ThreadPoolExecutor
        import asyncio

        mode = "full" if request.force_full else "incremental"
        loop = asyncio.get_event_loop()

        # Run the CPU/IO-bound indexing in a thread so the event loop isn't blocked
        result = await loop.run_in_executor(
            None,
            lambda: run_indexing(config.ingestion_catalog_path, mode),
        )

        # Reload the catalog cache after sync
        if profiler:
            profiler.loader.load_catalog(force=True)

        return SyncResponse(
            sync_id=str(uuid.uuid4()),
            status="completed",
            processed_count=result["inserted"],
            errors=[],
        )
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync operation failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
