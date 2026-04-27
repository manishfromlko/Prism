# Kubeflow Workspace Profiling Webapp

A generative AI-powered web application for profiling and analyzing Kubeflow workspaces. This project provides intelligent insights into data science workflows, ML pipelines, and collaborative patterns through advanced data ingestion, vector search, and LLM-powered analysis.

## Features

### 🚀 Current Implementation
- **Data Ingestion Pipeline**: Automated discovery and metadata extraction from Kubeflow workspaces
- **Guardrail Security**: Automatic detection and skipping of sensitive/unsupported files
- **Incremental Updates**: Efficient processing of only changed files
- **Audit Logging**: Complete compliance tracking for ingestion decisions
- **CLI Interface**: Command-line tool for easy pipeline execution
- **Vector Retrieval System**: FastAPI-based API for semantic search and workspace profiling
- **Workspace Profiling**: AI-powered insights into tools, topics, and collaboration patterns
- **Hybrid Search**: Combine vector similarity with keyword matching for better results

### 🔮 Upcoming Features
- **Langchain Orchestration**: Intelligent workflow analysis and chaining
- **Milvus Vector Database**: High-performance vector storage for embeddings
- **LiteLLM API Gateway**: Unified interface for multiple LLM providers
- **Langfuse Observability**: Comprehensive monitoring and tracing
- **Next.js Frontend**: Modern React-based user interface

## Retrieval API

The retrieval system provides RESTful APIs for semantic search and workspace profiling.

### Quick Start

1. **Set environment variables:**
   ```bash
   export MILVUS_HOST=localhost
   export MILVUS_PORT=19530
   export INGESTION_CATALOG_PATH=./data/catalog.json
   export EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```

2. **Start the API server:**
   ```bash
   cd src/retrieval
   python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Access the API documentation:**
   - OpenAPI docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### API Endpoints

#### Health Check
```bash
GET /health
```
Returns system health status including vector store and embedding service status.

#### Vector Search
```bash
POST /query
Content-Type: application/json

{
  "query": "machine learning classification",
  "top_k": 10,
  "use_hybrid": false
}
```
Performs semantic search across workspace artifacts.

#### Workspace Profiling
```bash
GET /profile/workspace/{workspace_id}
```
Returns AI-generated insights about a workspace including:
- Tool usage statistics
- Topic analysis
- Collaboration patterns
- Code metrics

#### System Metrics
```bash
GET /metrics
```
Returns performance metrics including query times, error rates, and memory usage.

#### Data Synchronization
```bash
POST /admin/sync
```
Triggers synchronization with the latest ingestion catalog.

### Example Usage

**Search for machine learning code:**
```python
import requests

response = requests.post("http://localhost:8000/query", json={
    "query": "neural network implementation",
    "top_k": 5,
    "use_hybrid": True
})

results = response.json()
for result in results["results"]:
    print(f"Artifact: {result['artifact_id']}")
    print(f"Content: {result['content'][:200]}...")
    print(f"Score: {result['score']}")
```

**Get workspace profile:**
```python
response = requests.get("http://localhost:8000/profile/workspace/ajay11.yadav")
profile = response.json()

print(f"Workspace: {profile['workspace_id']}")
print(f"Artifacts: {profile['artifact_count']}")
print("Top tools:", profile['top_tools'])
```

- Python 3.11+
- pip (Python package manager)
- Git

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd project-1
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install langchain litellm pymilvus pydantic pytest
   ```

4. **Install development dependencies (optional, for code quality):**
   ```bash
   pip install black flake8
   ```

## Usage

### Running the Ingestion Pipeline

The ingestion pipeline discovers workspaces, extracts metadata from notebooks and scripts, and stores the catalog in JSON format.

#### Full Ingestion (Initial Run)
```bash
PYTHONPATH=src python -m src.ingestion.cli --root dataset --mode full
```

#### Incremental Ingestion (Update Changed Files)
```bash
PYTHONPATH=src python -m src.ingestion.cli --root dataset --mode incremental
```

#### Dry Run (Validate Without Persisting)
```bash
PYTHONPATH=src python -m src.ingestion.cli --root dataset --mode full --dry-run
```

### Command Line Options

- `--root`: Path to the workspace root directory (required)
- `--mode`: `full` or `incremental` (default: full)
- `--dry-run`: Validate without persisting changes

### Output

The pipeline creates a `.ingestion/` directory in the root path containing:
- `ingestion_catalog.json`: Workspace and artifact metadata
- `ingestion_audit.json`: Audit log of ingestion decisions

## Testing

### Run All Tests
```bash
PYTHONPATH=src python -m pytest tests/ingestion/ -v
```

### Run Specific Test Categories
```bash
# Unit tests
PYTHONPATH=src python -m pytest tests/ingestion/unit/ -v

# Integration tests
PYTHONPATH=src python -m pytest tests/ingestion/integration/ -v
```

### Test Coverage
The test suite covers:
- Data model validation
- Guardrail pattern matching
- Storage operations
- Full pipeline execution
- Incremental updates
- Audit logging

## Code Quality

### Formatting
```bash
black src/ tests/
```

### Linting
```bash
flake8 src/ tests/
```

## Project Structure

```
project-1/
├── dataset/                    # Sample workspace data for testing
├── src/
│   └── ingestion/             # Ingestion pipeline modules
│       ├── cli.py             # Command-line interface
│       ├── pipeline.py        # Core ingestion logic
│       ├── storage.py         # JSON-based persistence
│       ├── guards.py          # Security guardrails
│       ├── extractors.py      # Metadata extraction
│       ├── models.py          # Data models
│       └── utils.py           # Utility functions
├── tests/
│   └── ingestion/             # Test suite
│       ├── unit/              # Unit tests
│       └── integration/       # Integration tests
├── specs/
│   └── 001-data-ingestion-pipeline/  # Feature specifications
└── README.md                  # This file
```

## Development

### Adding New Features
1. Create a new spec in `specs/` following the naming convention
2. Implement the feature in phases with clear acceptance criteria
3. Add comprehensive tests
4. Update documentation

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file in the dataset directory for details.

## Roadmap

- [x] Data Ingestion Pipeline (MVP)
- [ ] Langchain Orchestration and Vector Retrieval
- [ ] LiteLLM API Gateway Implementation
- [ ] Langfuse Observability Stack
- [ ] Next.js Frontend Development
- [ ] Production Deployment</content>
<parameter name="filePath">/Users/manish/mount/projects/project-1/README.md