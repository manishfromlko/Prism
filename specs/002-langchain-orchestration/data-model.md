# Data Models: Langchain Orchestration and Vector Retrieval

## Overview

This document defines the data models and schemas used in the vector retrieval system, building upon the ingestion pipeline's catalog structure.

## Core Data Models

### Document (Langchain Document)

Represents a processable text unit from workspace artifacts.

```python
@dataclass
class ProcessedDocument:
    page_content: str                    # Text content
    metadata: Dict[str, Any]            # Artifact metadata
    artifact_id: str                    # Unique identifier
    workspace_id: str                   # Parent workspace
    content_type: str                   # notebook, script, etc.
    chunk_index: int                    # For split documents
    total_chunks: int                   # Total chunks in document
```

### Embedding Record

Stores vector embeddings with associated metadata.

```python
@dataclass
class EmbeddingRecord:
    artifact_id: str                    # Reference to document
    vector: List[float]                 # Embedding vector
    model_name: str                     # Embedding model used
    created_at: datetime               # Generation timestamp
    metadata: Dict[str, Any]           # Additional context
```

### Vector Search Result

Response structure for similarity search queries.

```python
@dataclass
class SearchResult:
    artifact_id: str                    # Matching artifact
    content: str                       # Relevant content snippet
    metadata: Dict[str, Any]           # Artifact metadata
    score: float                       # Similarity score
    rank: int                          # Result ranking
```

## API Data Models

### Query Request

```python
class QueryRequest(BaseModel):
    query: str                         # Search query
    workspace_ids: Optional[List[str]] = None
    top_k: int = 10
    threshold: Optional[float] = None
    filters: Optional[Dict[str, Any]] = None
```

### Query Response

```python
class QueryResponse(BaseModel):
    results: List[SearchResult]
    total_found: int
    query_time_ms: int
    query: str
```

### Workspace Profile

```python
class WorkspaceProfile(BaseModel):
    workspace_id: str
    artifact_count: int
    top_tools: List[Dict[str, Any]]
    top_topics: List[Dict[str, Any]]
    collaboration_patterns: Dict[str, Any]
    last_updated: Optional[datetime]
```

## Configuration Models

### Retrieval Configuration

```python
class RetrievalConfig(BaseModel):
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    collection_name: str = "kubeflow_artifacts"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    batch_size: int = 32
    similarity_metric: str = "COSINE"
    index_type: str = "HNSW"
```

## Storage Schema

### Milvus Collection Schema

```
Collection: kubeflow_artifacts
Fields:
- id: INT64 (primary key, auto-increment)
- artifact_id: VARCHAR(255)
- vector: FLOAT_VECTOR(384)  # Dimension depends on model
- content: VARCHAR(5000)     # Content snippet
- metadata: JSON             # Full metadata
- created_at: TIMESTAMP
Indexes:
- vector: HNSW index with COSINE metric
- artifact_id: String index
```

## Data Flow Models

### Processing Pipeline

1. **Ingestion Catalog** → Document Loader → **ProcessedDocument**
2. **ProcessedDocument** → Embedding Service → **EmbeddingRecord**
3. **EmbeddingRecord** → Vector Store → **Milvus Collection**
4. **Query** → Retriever → **SearchResult**

### Incremental Updates

- Track `last_ingestion_sync` timestamp
- Compare with ingestion catalog modification time
- Process only changed artifacts
- Update existing vectors or insert new ones

## Validation Rules

- Embedding vectors must match model dimensions
- Artifact IDs must be unique within workspace
- Metadata must include required fields from ingestion
- Similarity scores must be between 0.0 and 1.0
- Content snippets limited to 5000 characters

## Error Models

```python
class RetrievalError(BaseModel):
    error_type: str                    # connection, processing, validation
    message: str                       # Error description
    artifact_id: Optional[str]         # Related artifact if applicable
    timestamp: datetime               # Error occurrence time
```</content>
<parameter name="filePath">/Users/manish/mount/projects/project-1/specs/002-langchain-orchestration/data-model.md