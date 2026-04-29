# Kubeflow Workspace Profiling Webapp

A generative AI-powered web application for profiling and analyzing Kubeflow workspaces. Provides intelligent insights into data science workflows, ML pipelines, and collaboration patterns through automated data ingestion, vector search, and LLM-powered analysis.

## Architecture Overview

```
Phase 1: Data Ingestion   →  dataset/.ingestion/ingestion_catalog.json
Phase 2: Vector Retrieval →  Milvus (port 19530) + FastAPI (any port, default 8000)
Phase 3: Webapp Frontend  →  Next.js (port 3000) — proxies /api/* to FastAPI
Phase 4: LLM Generation   →  LiteLLM + Langfuse (upcoming)
```

**How the webapp talks to the backend:**
The Next.js webapp does NOT call the Python backend directly from the browser.
It has server-side API route handlers at `/api/*` (in `webapp/app/api/`) that proxy and
transform requests to the Python FastAPI backend. The Python backend URL is configured
via `PYTHON_API_URL` (default: `http://localhost:8000`).

## Prerequisites

- Python 3.11+
- Docker (for Milvus vector database)
- Node.js 18+ (for webapp)

---

## Step-by-Step: Running the Full Stack

### Step 1 — Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 2 — Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note on version pins:** `sentence-transformers<3`, `transformers<5`, and `numpy<2` are pinned
> because torch 2.2.x is incompatible with numpy 2.x (`_ARRAY_API not found` crash) and with
> transformers 5.x (`NameError: name 'nn' is not defined`).

### Step 3 — Run the data ingestion pipeline

```bash
python -m src.ingestion.cli --root dataset/ --mode full
```

Expected output:
```
Ingestion complete: 4 workspaces, 178 artifacts
Catalog written to: dataset/.ingestion/ingestion_catalog.json
```

For subsequent runs, process only changed files:
```bash
python -m src.ingestion.cli --root dataset/ --mode incremental
```

Dry run (validate without writing):
```bash
python -m src.ingestion.cli --root dataset/ --mode full --dry-run
```

### Step 4 — Start Milvus (vector database)

```bash
docker run -d \
  --name milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:v2.6.14 standalone
```

Wait ~10 seconds, then verify:
```bash
docker logs milvus 2>&1 | tail -5
```

### Step 5 — Populate the vector store

Run once (or after re-ingestion). This loads documents from the catalog, generates 384-dim
embeddings with `all-MiniLM-L6-v2`, and inserts them into Milvus:

```bash
INGESTION_CATALOG_PATH=dataset/.ingestion/ingestion_catalog.json python -c "
from src.retrieval.config import RetrievalConfig
from src.retrieval.document_loader import DocumentLoader
from src.retrieval.embeddings import EmbeddingService
from src.retrieval.vector_store import VectorStore

config = RetrievalConfig.from_env()

store = VectorStore(config)
store.create_collection()

loader = DocumentLoader('dataset/.ingestion/ingestion_catalog.json', config)
documents = loader.load_documents()

embedder = EmbeddingService(config)
texts = [doc.page_content for doc in documents]
embeddings = embedder.generate_embeddings(texts)

artifact_ids = [doc.metadata.get('artifact_id', '') for doc in documents]
contents = [doc.page_content[:5000] for doc in documents]
metadatas = [doc.metadata for doc in documents]

store.insert_vectors(artifact_ids, embeddings, contents, metadatas)
print(f'Inserted {len(documents)} vectors into Milvus')
"
```

Expected output:
```
Loaded 301 documents from 178 artifacts
Applied guardrails: 298/301 documents retained
Inserted 298 vectors into Milvus
```

### Step 6 — Start the retrieval API

Choose a free port. If port 8000 is already in use (e.g., by Docker or another service),
use a different port and note it for Step 8.

```bash
INGESTION_CATALOG_PATH=dataset/.ingestion/ingestion_catalog.json \
  python -m uvicorn src.retrieval.api:app --host 0.0.0.0 --port 8000
```

> **Important:** Always use `python -m uvicorn` (not bare `uvicorn`) to use the active venv.
> Run from the project root, not from inside `src/retrieval/`.

Verify the API is healthy:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "vector_store": {"connected": true, "total_vectors": 298},
  "embedding_service": {"model_loaded": true, "model_name": "all-MiniLM-L6-v2"}
}
```

Check the new workspace list endpoint:
```bash
curl http://localhost:8000/workspaces
```

### Step 7 — Test semantic search (optional smoke test)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning with pyspark", "top_k": 3}'
```

Expected: 3 results with cosine similarity scores (~0.6–0.7).

### Step 8 — Install webapp dependencies

```bash
cd webapp
npm install
```

### Step 9 — Start the webapp

```bash
# If your API is on port 8000 (default):
cd webapp
npm run dev

# If your API is on a different port (e.g., 8002 because 8000 is taken):
cd webapp
PYTHON_API_URL=http://localhost:8002 npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

**How routing works:** The webapp makes all requests to its own `/api/*` routes (e.g.,
`/api/workspaces`, `/api/search`). Each Next.js API route handler proxies the call to the
Python backend at `PYTHON_API_URL` and transforms the response shape. This means the browser
never needs a direct connection to the Python backend.

---

## Python API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health: vector store, embedding service, cache |
| `GET` | `/metrics` | Uptime, query count, avg latency, memory usage |
| `GET` | `/workspaces` | List all workspaces from the ingestion catalog |
| `GET` | `/workspaces/{id}` | Get a single workspace by ID |
| `POST` | `/query` | Semantic search across workspace artifacts |
| `GET` | `/profile/workspace/{id}` | AI-powered workspace insights |
| `POST` | `/admin/sync` | Trigger re-sync with ingestion catalog |
| `GET` | `/docs` | Interactive OpenAPI documentation |

### Search request body

```json
{
  "query": "neural network classification",
  "top_k": 10,
  "workspace_ids": ["ajay11.yadav"],
  "use_hybrid": false
}
```

Set `use_hybrid: true` to combine vector similarity with keyword matching.

---

## Next.js API Routes (proxy layer)

These are server-side only — they live at `webapp/app/api/` and bridge the browser to the
Python backend:

| Webapp route | Proxies to |
|---|---|
| `GET /api/workspaces` | `GET /workspaces` |
| `GET /api/workspaces/{id}` | `GET /workspaces/{id}` |
| `GET /api/workspaces/{id}/profile` | `GET /profile/workspace/{id}` |
| `POST /api/search` | `POST /query` (+ response transform) |
| `GET /api/health` | `GET /health` (+ response transform) |
| `GET /api/metrics` | `GET /metrics` |
| `POST /api/admin/sync` | `POST /admin/sync` |

---

## Environment Variables

### Python backend

| Variable | Default | Description |
|----------|---------|-------------|
| `MILVUS_HOST` | `localhost` | Milvus server host |
| `MILVUS_PORT` | `19530` | Milvus server port |
| `MILVUS_COLLECTION` | `kubeflow_artifacts` | Collection name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `INGESTION_CATALOG_PATH` | `./data/catalog.json` | **Must override** — path to the catalog JSON |
| `BATCH_SIZE` | `32` | Embedding batch size |

### Webapp (Next.js)

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON_API_URL` | `http://localhost:8000` | Python backend URL (server-side only, not exposed to browser) |

Set in environment or create `webapp/.env.local`:
```bash
PYTHON_API_URL=http://localhost:8002
```

---

## Project Structure

```
project-1/
├── dataset/                         # Sample Kubeflow workspace data
│   └── .ingestion/                  # Generated by ingestion pipeline
│       ├── ingestion_catalog.json   # Workspace + artifact metadata
│       └── ingestion_audit.json     # Guardrail audit log
├── src/
│   ├── ingestion/                   # Phase 1: data ingestion
│   │   ├── cli.py                   # Entry point (python -m src.ingestion.cli)
│   │   ├── pipeline.py              # Discovery, classification, extraction
│   │   ├── storage.py               # JSON catalog persistence
│   │   ├── guards.py                # Sensitive file detection
│   │   ├── extractors.py            # Notebook and script metadata
│   │   ├── models.py                # Dataclasses: Workspace, FileArtifact, etc.
│   │   └── utils.py                 # SHA256 hashing, safe I/O
│   └── retrieval/                   # Phase 2: vector retrieval
│       ├── api.py                   # FastAPI application
│       ├── config.py                # RetrievalConfig (env-driven)
│       ├── embeddings.py            # SentenceTransformer + MD5 cache
│       ├── vector_store.py          # Milvus HNSW collection (384-dim)
│       ├── document_loader.py       # Catalog → LangChain Documents
│       ├── document_guard.py        # Document-level content filtering
│       ├── retriever.py             # VectorRetriever + HybridRetriever
│       ├── text_processor.py        # Text chunking
│       └── profiling.py             # WorkspaceProfiler
├── webapp/                          # Phase 3: Next.js frontend
│   ├── app/
│   │   ├── api/                     # Server-side proxy routes (Next.js API routes)
│   │   │   ├── workspaces/          # GET /api/workspaces, /api/workspaces/[id]
│   │   │   ├── search/              # POST /api/search
│   │   │   ├── health/              # GET /api/health
│   │   │   ├── metrics/             # GET /api/metrics
│   │   │   └── admin/sync/          # POST /api/admin/sync
│   │   ├── workspaces/              # Workspace list + detail pages
│   │   ├── search/                  # Semantic search page
│   │   ├── analytics/               # System metrics page
│   │   └── settings/                # Settings page
│   ├── components/                  # React UI components
│   ├── hooks/use-api.ts             # React Query hooks
│   ├── lib/api.ts                   # API client (relative URLs → Next.js /api/*)
│   ├── next.config.js               # PYTHON_API_URL forwarded to API routes
│   └── types/index.ts               # TypeScript types
├── tests/
│   ├── ingestion/unit/
│   ├── ingestion/integration/
│   └── test_retrieval_api.py
├── specs/                           # Feature specifications and plans
├── airflow/                         # Airflow DAG for scheduled ingestion
├── requirements.txt                 # Python dependencies (version-pinned)
├── docker-compose.yml               # Full stack: API + webapp + Milvus
├── docker-compose.airflow.yml       # Airflow orchestration stack
└── Dockerfile                       # Backend container
```

---

## Testing

```bash
# All tests
python -m pytest tests/ -v

# Ingestion unit tests
python -m pytest tests/ingestion/unit/ -v

# Ingestion integration tests
python -m pytest tests/ingestion/integration/ -v

# Retrieval API tests
python -m pytest tests/test_retrieval_api.py -v
```

---

## Docker Deployment

```bash
docker compose up --build
```

- API: http://localhost:8000
- Webapp: http://localhost:3000

Run ingestion inside the backend container:
```bash
docker compose exec backend python -m src.ingestion.cli --root /data --mode full
```

---

## Airflow Orchestration

```bash
docker compose -f docker-compose.airflow.yml up --build
```

Airflow UI at http://localhost:8080 — credentials: `admin` / `admin`.
The DAG at `airflow/dags/ingestion_dag.py` runs the ingestion CLI on a schedule.

---

## Roadmap

- [x] Phase 1: Data Ingestion Pipeline
- [x] Phase 2: Vector Retrieval + FastAPI
- [x] Phase 3: Next.js Webapp Frontend (fully integrated)
- [ ] Phase 4: LiteLLM API Gateway
- [ ] Phase 4: Langfuse Observability
- [ ] Production deployment
