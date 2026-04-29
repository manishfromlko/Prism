# Quickstart: Langchain Orchestration and Vector Retrieval

This guide provides quick setup and usage instructions for the vector retrieval system.

## Prerequisites

- Completed data ingestion pipeline (see `specs/001-data-ingestion-pipeline/quickstart.md`)
- Python 3.11+ with virtual environment
- Running Milvus instance (local or cloud)

## Installation

1. **Install additional dependencies:**
   ```bash
   pip install langchain pymilvus sentence-transformers fastapi uvicorn
   ```

2. **Start Milvus (if running locally):**
   ```bash
   # Using Docker
   docker run -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone
   ```

## Configuration

Create a configuration file or environment variables:

```python
# src/retrieval/config.py
MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "kubeflow_artifacts"
```

## Usage

### Initialize Vector Store

```bash
PYTHONPATH=src python -c "
from src.retrieval.vector_store import VectorStore
from src.retrieval.config import Config

config = Config()
store = VectorStore(config)
store.create_collection()
print('Vector store initialized')
"
```

### Process and Store Documents

```bash
PYTHONPATH=src python -c "
from src.retrieval.document_loader import DocumentLoader
from src.retrieval.embeddings import EmbeddingService
from src.retrieval.vector_store import VectorStore
from src.retrieval.config import Config

config = Config()
loader = DocumentLoader('dataset/.ingestion/ingestion_catalog.json')
embedder = EmbeddingService(config)
store = VectorStore(config)

documents = loader.load_documents()
embeddings = embedder.generate_embeddings(documents)
store.insert_vectors(documents, embeddings)
print(f'Processed {len(documents)} documents')
"
```

### Start Query API

```bash
PYTHONPATH=src uvicorn src.retrieval.api:app --host 0.0.0.0 --port 8000
```

### Query Examples

```bash
# Semantic search
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning algorithms", "top_k": 5}'

# Workspace profiling
curl -X GET "http://localhost:8000/profile/workspace/amit23.sharma"
```

## Testing

### Run Retrieval Tests
```bash
PYTHONPATH=src python -m pytest tests/retrieval/ -v
```

### Manual Testing
1. Ensure ingestion catalog exists
2. Initialize vector store
3. Process documents
4. Start API server
5. Test queries via curl or API client

## Troubleshooting

- **Milvus connection issues**: Check if Milvus is running on correct host/port
- **Embedding model errors**: Verify model name and internet connection for downloads
- **Memory issues**: Reduce batch size in embedding generation for large datasets
- **API timeouts**: Increase timeout values for large similarity searches

## Performance Tips

- Use GPU for embedding generation if available
- Batch document processing for efficiency
- Implement caching for frequently queried embeddings
- Monitor Milvus resource usage and scale as needed</content>
<parameter name="filePath">/Users/manish/mount/projects/project-1/specs/002-langchain-orchestration/quickstart.md