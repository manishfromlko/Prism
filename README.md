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

### Step 3 — Create the `.env` file

Create a `.env` file at the project root (already gitignored):

```bash
cat > .env <<'EOF'
OPENAI_API_KEY=<your-openai-api-key>
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
INGESTION_CATALOG_PATH=dataset/.ingestion/ingestion_catalog.json
EOF
```

The Python backend loads `.env` automatically at startup — no need to export env vars manually.

> **Note:** The embedding model is `text-embedding-3-small` (OpenAI, 1536-dim). A valid
> `OPENAI_API_KEY` is required; the server refuses to start without it.

### Step 4 — Run the data ingestion pipeline

Only **Jupyter notebooks** (`.ipynb`), **scripts** (`.py`, `.scala`, `.sql`), and **text files**
(`.txt`, `.md`) are catalogued. CSV files and other data files are intentionally excluded — the
goal is to understand *what people are working on*, not to index their datasets.

```bash
python -m src.ingestion.cli --root dataset/ --mode full
```

Expected output:
```
Done — 5 workspaces, 211 artifacts (132 notebooks, 75 scripts, 4 text)
```

For subsequent runs, process only changed files:
```bash
python -m src.ingestion.cli --root dataset/ --mode incremental
```

### Step 5 — Start Milvus (vector database)

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

### Step 6 — Index artifacts into Milvus

Run the indexer after every ingestion to keep the vector store in sync with the catalog.
It is **safe to run multiple times** — incremental mode queries Milvus first and only inserts
artifact IDs not already present, so there are no duplicate vectors.

```bash
# First run (or after adding new workspaces to the catalog):
python -m src.retrieval.indexer \
  --catalog dataset/.ingestion/ingestion_catalog.json \
  --mode incremental
```

Expected output:
```
Already indexed: 0 artifacts
Catalog contains 190 indexable documents
To index: 190 new | skipping: 0 already present
Generating embeddings for 190 documents...
Inserting vectors into Milvus...
Done — inserted: 190, skipped: 0, total: 190
```

Running it again (nothing changed):
```
Already indexed: 190 artifacts
To index: 0 new | skipping: 190 already present
Done — inserted: 0, skipped: 190, total: 190
```

To fully rebuild the index from scratch (e.g., after re-ingestion):
```bash
python -m src.retrieval.indexer \
  --catalog dataset/.ingestion/ingestion_catalog.json \
  --mode full
```

### Step 7 — Start the retrieval API

All configuration is read from `.env` automatically. Run from the project root:

```bash
python -m uvicorn src.retrieval.api:app --host 0.0.0.0 --port 8000
```

If port 8000 is already in use, use another port and note it for Step 10:

```bash
python -m uvicorn src.retrieval.api:app --host 0.0.0.0 --port 8002
```

Verify the API is healthy:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "vector_store": {"connected": true, "total_vectors": 190},
  "embedding_service": {"model_loaded": true, "model_name": "text-embedding-3-small"}
}
```

Check the new workspace list endpoint:
```bash
curl http://localhost:8000/workspaces
```

### Step 8 — Test semantic search (optional smoke test)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning with pyspark", "top_k": 3}'
```

Expected: 3 results with cosine similarity scores (~0.6–0.7).

### Step 9 — Install webapp dependencies

```bash
cd webapp
npm install
```

### Step 10 — Start the webapp

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
| `POST` | `/admin/sync` | Re-index catalog into Milvus (`force_full: true` to rebuild) |
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

Set all of these in the `.env` file at the project root (loaded automatically):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key for embeddings |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `EMBEDDING_DIMENSION` | `1536` | Must match the model's output dimension |
| `MILVUS_HOST` | `localhost` | Milvus server host |
| `MILVUS_PORT` | `19530` | Milvus server port |
| `MILVUS_COLLECTION` | `kubeflow_artifacts` | Collection name |
| `INGESTION_CATALOG_PATH` | `dataset/.ingestion/ingestion_catalog.json` | Path to the catalog JSON |
| `BATCH_SIZE` | `32` | Embeddings per OpenAI API request |

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
│       ├── indexer.py               # CLI: embed catalog artifacts → insert into Milvus
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
