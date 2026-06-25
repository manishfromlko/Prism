# RAG Chatbot Legacy

Minimal local stack for a multi-agent RAG chatbot over workspace artifacts, user profiles, and platform documents.

## Runtime

- `frontend/` - Next.js UI and proxy API routes.
- `backend/` - FastAPI API, ingestion, retrieval, agents, memory, and tracing.
- `data/workspaces/` - Lightweight sample user workspaces and ingestion catalog.
- `data/platform_documents/` - Word documents indexed into the `platform_docs` collection.
- `docker-compose.yml` - Qdrant, backend, frontend, and MLflow.

## Quick Start

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. Start dependencies and app services:

```bash
docker compose up -d --build
```

3. If Qdrant is empty, run ingestion from the backend container:

```bash
docker compose exec backend python -m src.ingestion.cli --root /app/data/workspaces --mode incremental
docker compose exec backend python -m src.retrieval.indexer --mode incremental
docker compose exec backend python -m src.retrieval.artifact_summary_indexer --mode incremental
docker compose exec backend python -m src.retrieval.profile_from_summaries_indexer --mode incremental
docker compose exec backend python -m src.retrieval.chatbot.doc_ingestion
```

4. Open the apps:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000/docs>
- Qdrant: <http://localhost:6333/dashboard>
- MLflow: <http://localhost:5001>

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Local Setup](docs/LOCAL_SETUP.md)
- [Ingestion](docs/INGESTION.md)
- [Observability](docs/OBSERVABILITY.md)
- [API](docs/API.md)

