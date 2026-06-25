# Local Setup

## Prerequisites

- Docker Desktop
- OpenAI API key
- Optional: `uv`, Python 3.11+, Node.js 20+

## Environment

Create `.env` from `.env.example` at the repository root:

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY`. Leave LangSmith disabled unless you have a paid/available account. MLflow is enabled locally by default.

## Docker

```bash
docker compose up -d --build
docker compose ps
```

Services:

- Frontend: <http://localhost:3000>
- Backend docs: <http://localhost:8000/docs>
- Qdrant dashboard: <http://localhost:6333/dashboard>
- MLflow UI: <http://localhost:5001>

## Local Backend Tests

```bash
cd backend
uv run pytest tests/retrieval/unit
```

If dependency downloads time out, use an already synced virtualenv or rerun `uv run` after the cache has partially populated.

## Local Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `PYTHON_API_URL=http://localhost:8000` when running outside Docker if needed.

