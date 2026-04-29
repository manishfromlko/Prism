# API Contract: Vector Retrieval and Profiling

This contract defines the external interface for vector-based retrieval and workspace profiling.

## POST /query

Perform semantic similarity search across workspace artifacts.

### Request
- `query` (string, required): Search query text
- `workspace_ids` (array<string>, optional): Limit search to specific workspaces
- `top_k` (integer, optional): Number of results to return (default: 10)
- `threshold` (float, optional): Similarity threshold (0.0-1.0)

### Response
- `results` (array<object>): Search results
  - `artifact_id` (string): Unique artifact identifier
  - `content` (string): Relevant content snippet
  - `metadata` (object): Artifact metadata
  - `score` (float): Similarity score
- `total_found` (integer): Total matching artifacts
- `query_time_ms` (integer): Search execution time

## GET /profile/workspace/{workspace_id}

Get profiling insights for a specific workspace.

### Response
- `workspace_id` (string): Workspace identifier
- `artifact_count` (integer): Number of artifacts
- `top_tools` (array<object>): Most used tools/frameworks
  - `tool` (string): Tool name
  - `count` (integer): Usage count
- `top_topics` (array<object>): Main topics/themes
  - `topic` (string): Topic name
  - `relevance` (float): Relevance score
- `collaboration_patterns` (object): Collaboration insights
- `last_updated` (string, datetime)

## GET /health

Check system health and status.

### Response
- `status` (string): `healthy`, `degraded`, `unhealthy`
- `vector_store` (object): Milvus status
  - `connected` (boolean)
  - `collection_count` (integer)
  - `total_vectors` (integer)
- `embedding_service` (object): Embedding service status
  - `model_loaded` (boolean)
  - `model_name` (string)
- `last_ingestion_sync` (string, datetime|null)

## POST /admin/sync

Trigger synchronization with latest ingestion catalog.

### Request
- `force_full` (boolean, optional): Force full reprocessing instead of incremental

### Response
- `sync_id` (string): Synchronization job identifier
- `status` (string): `started`, `running`, `completed`, `failed`
- `processed_count` (integer): Number of artifacts processed
- `errors` (array<string>): Any error messages</content>
<parameter name="filePath">/Users/manish/mount/projects/project-1/specs/002-langchain-orchestration/contracts/retrieval-api.md