# Installation

## Clone and Enter the Repo

```bash
git clone <repo-url>
cd project-1
```

All commands in this documentation assume the repository root as the working directory unless stated otherwise.

## Python Setup

Preferred:

```bash
python3.11 --version
pip install uv
uv sync
```

Fallback:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The code imports packages beyond the small `pyproject.toml` dependency list, so `requirements.txt` is the more explicit fallback source.

## Node Setup

```bash
cd webapp
npm install
cd ..
```

The webapp uses Next.js 15, React 18, Tailwind CSS, shadcn-style UI components, TanStack Query, and Recharts.

## Docker Setup

Docker is required for the local Qdrant vector database.

```bash
docker compose up -d qdrant
```

Verify:

```bash
docker ps
docker logs kubeflow-qdrant
```

The compose service exposes Qdrant on `localhost:6333`.

## Environment Variables

Create `.env` in the repository root:

```bash
OPENAI_API_KEY=<your-openai-api-key>
QDRANT_HOST=127.0.0.1
QDRANT_PORT=6333
QDRANT_COLLECTION=kubeflow_artifacts
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
INGESTION_CATALOG_PATH=dataset/.ingestion/ingestion_catalog.json
PROFILE_LLM_MODEL=gpt-4o-mini
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=sk-1234
PYTHON_API_URL=http://localhost:8000
```

Important notes:

- `src/retrieval/config.py` loads `.env` automatically.
- The current retrieval code is built around OpenAI-compatible embeddings with dimension `1536`.
- `make_openai_client()` points LLM calls at `LITELLM_BASE_URL`. If LiteLLM is not running, calls that use that client can fail unless you point it to a compatible endpoint.
- The Next.js route handlers read `PYTHON_API_URL` server-side. The default is `http://localhost:8000`.

## Optional Observability Setup

LiteLLM:

```bash
cd rag-observability/litellm
cp .env.example .env
docker compose up -d
```

Langfuse:

```bash
cd rag-observability/langfuse
cp .env.example .env
docker compose up -d
```

Read [Observability and Evaluation](./components/05-OBSERVABILITY-AND-EVALUATION.md) before treating this as production monitoring.

## Optional Airflow Setup

Airflow is only needed to schedule ingestion. The local product can run without it.

```bash
docker compose -f docker-compose.airflow.yml up -d
```

See [Orchestration](./components/04-ORCHESTRATION.md).

## Optional Databricks Setup

The `databricks/` directory contains a migration path that replaces Qdrant, LiteLLM, local FastAPI hosting, and filesystem storage with Databricks-native services. It is not required for local development.
