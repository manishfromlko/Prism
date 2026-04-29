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
from .user_profile_store import UserProfileStore
from .profile_indexer import run_profile_indexing
from .profile_from_summaries_indexer import run_profile_indexing_from_summaries
from .artifact_summary_store import ArtifactSummaryStore
from .artifact_summary_indexer import run_artifact_summary_indexing

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
user_profile_store: Optional[UserProfileStore] = None
artifact_summary_store: Optional[ArtifactSummaryStore] = None

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
    global config, vector_store, embedding_service, query_processor, profiler, user_profile_store, artifact_summary_store
    try:
        config = RetrievalConfig.from_env()
        vector_store = VectorStore(config)
        embedding_service = EmbeddingService(config)
        query_processor = QueryProcessor(config)
        profiler = WorkspaceProfiler(config, config.ingestion_catalog_path)
        vector_store.create_collection()

        # Pre-load kubeflow_artifacts collection into Milvus memory
        if vector_store.collection:
            vector_store.collection.load()
            vector_store._collection_loaded = True

        # Load user_profiles collection (non-fatal if not yet indexed)
        try:
            user_profile_store = UserProfileStore(config)
            user_profile_store.create_collection(drop_if_exists=False)
            user_profile_store._ensure_loaded()
        except Exception as e:
            logger.warning(f"User profile store not ready: {e}")
            user_profile_store = None

        # Load artifact_summaries collection (non-fatal if not yet indexed)
        try:
            artifact_summary_store = ArtifactSummaryStore(config)
            artifact_summary_store.create_collection(drop_if_exists=False)
            artifact_summary_store._ensure_loaded()
        except Exception as e:
            logger.warning(f"Artifact summary store not ready: {e}")
            artifact_summary_store = None

        # Pre-warm the catalog cache
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

# ---------------------------------------------------------------------------
# User profiles endpoints
# ---------------------------------------------------------------------------

@app.get("/user-profiles")
async def list_user_profiles():
    """Return all user profiles stored in the user_profiles collection."""
    if not user_profile_store:
        raise HTTPException(status_code=503, detail="User profile store not initialized. Run profile_indexer first.")
    try:
        profiles = user_profile_store.get_all_profiles()
        data = []
        for p in profiles:
            data.append({
                "id": str(p.get("id", "")),
                "user_id": p.get("user_id", ""),
                "user_profile": p.get("user_profile", ""),
                "tags": [t.strip() for t in p.get("tags", "").split(",") if t.strip()],
            })
        return {"data": data, "total": len(data)}
    except Exception as e:
        logger.error(f"Failed to list user profiles: {e}")
        raise HTTPException(status_code=500, detail="Failed to list user profiles")


@app.get("/user-profiles/{user_id}")
async def get_user_profile(user_id: str):
    """Return the profile for a single user."""
    if not user_profile_store:
        raise HTTPException(status_code=503, detail="User profile store not initialized.")
    try:
        p = user_profile_store.get_profile(user_id)
        if not p:
            raise HTTPException(status_code=404, detail=f"Profile for '{user_id}' not found")
        return {
            "data": {
                "id": str(p.get("id", "")),
                "user_id": p.get("user_id", ""),
                "user_profile": p.get("user_profile", ""),
                "tags": [t.strip() for t in p.get("tags", "").split(",") if t.strip()],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")


@app.post("/admin/sync-profiles")
async def sync_profiles():
    """Re-generate and re-index all user profiles from the catalog (raw-file approach)."""
    if not config:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_profile_indexing(config.ingestion_catalog_path),
        )
        global user_profile_store
        user_profile_store = UserProfileStore(config)
        user_profile_store.create_collection(drop_if_exists=False)
        return {"status": "completed", "profiles_indexed": result["inserted"]}
    except Exception as e:
        logger.error(f"Profile sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Profile sync failed: {e}")


@app.post("/admin/sync-profiles-from-summaries")
async def sync_profiles_from_summaries():
    """
    Re-generate and re-index user profiles using artifact summaries from Milvus
    as LLM context (gpt-4o-mini, ≤5-line summaries).

    Requires the artifact_summaries collection to be populated first.
    Call POST /admin/sync-artifact-summaries before this endpoint.
    """
    if not config:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_profile_indexing_from_summaries(drop_existing=True),
        )
        global user_profile_store
        user_profile_store = UserProfileStore(config)
        user_profile_store.create_collection(drop_if_exists=False)
        user_profile_store._ensure_loaded()
        return {"status": "completed", "profiles_indexed": result["inserted"]}
    except Exception as e:
        logger.error(f"Profile sync from summaries failed: {e}")
        raise HTTPException(status_code=500, detail=f"Profile sync from summaries failed: {e}")


@app.get("/artifact-summaries")
async def get_artifact_summary(
    workspace_id: str = Query(..., description="Workspace ID"),
    artifact_id: str = Query(..., description="Artifact ID"),
):
    """Return summary for one artifact under a workspace."""
    if not artifact_summary_store:
        raise HTTPException(status_code=503, detail="Artifact summary store not initialized.")
    try:
        summary = artifact_summary_store.get_summary(workspace_id, artifact_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Artifact summary not found")
        return {
            "data": {
                "id": str(summary.get("id", "")),
                "user_id": summary.get("user_id", ""),
                "artifact_id": summary.get("artifact_id", ""),
                "artifact_summary": summary.get("artifact_summary", ""),
                "tags": [t.strip() for t in summary.get("tags", "").split(",") if t.strip()],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get artifact summary for {workspace_id}/{artifact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get artifact summary")


@app.get("/artifact-summaries/workspace/{workspace_id}")
async def list_artifact_summaries(workspace_id: str):
    """Return all artifact summaries for a workspace."""
    if not artifact_summary_store:
        raise HTTPException(status_code=503, detail="Artifact summary store not initialized.")
    try:
        summaries = artifact_summary_store.get_workspace_summaries(workspace_id)
        data = []
        for s in summaries:
            data.append({
                "id": str(s.get("id", "")),
                "user_id": s.get("user_id", ""),
                "artifact_id": s.get("artifact_id", ""),
                "artifact_summary": s.get("artifact_summary", ""),
                "tags": [t.strip() for t in s.get("tags", "").split(",") if t.strip()],
            })
        return {"data": data, "total": len(data)}
    except Exception as e:
        logger.error(f"Failed to list artifact summaries for {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list artifact summaries")


@app.post("/admin/sync-artifact-summaries")
async def sync_artifact_summaries(force_full: bool = False):
    """Generate and index artifact summaries into Milvus."""
    if not config:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        mode = "full" if force_full else "incremental"
        result = await loop.run_in_executor(
            None,
            lambda: run_artifact_summary_indexing(config.ingestion_catalog_path, mode),
        )
        global artifact_summary_store
        artifact_summary_store = ArtifactSummaryStore(config)
        artifact_summary_store.create_collection(drop_if_exists=False)
        return {"status": "completed", "mode": mode, "summaries_indexed": result["inserted"]}
    except Exception as e:
        logger.error(f"Artifact summary sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Artifact summary sync failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
