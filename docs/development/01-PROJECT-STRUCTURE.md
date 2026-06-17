# Project Structure

```text
.
├── src/
│   ├── ingestion/            # Dataset scanning, metadata extraction, catalog/audit writes
│   ├── retrieval/            # FastAPI, Qdrant stores, indexing, retrieval, profiling, chatbot
│   └── observability/        # Trace scoring and background evaluation helpers
├── webapp/                   # Next.js frontend and proxy API routes
├── dataset/                  # Example/user workspace artifacts
├── platform_documents/       # Word documents ingested for platform docs Q&A
├── prompts/                  # LLM prompt templates for summaries, profiles, and chatbot
├── tests/                    # Unit and integration tests
├── evaluation/               # Chatbot evaluation dataset and runner
├── airflow/                  # Optional Airflow DAG
├── databricks/               # Optional Databricks migration assets
├── rag-observability/        # LiteLLM and Langfuse compose stacks
├── specs/                    # Historical implementation specs
├── presentation/             # Slide decks and generated architecture diagrams
└── docs/                     # Canonical documentation
```

## Backend Layout

| Directory | Notes |
| --- | --- |
| `src/ingestion` | Pure batch pipeline. Does not require FastAPI. |
| `src/retrieval` | Runtime services and batch indexers share config and store adapters. |
| `src/retrieval/chatbot` | Chatbot-specific retrieval, prompts, routing, formatting, and doc ingestion. |
| `src/observability` | Optional tracing/evaluation helpers used by chatbot runtime. |

## Frontend Layout

| Directory | Notes |
| --- | --- |
| `webapp/app` | Next.js app router pages and route handlers. |
| `webapp/components` | UI building blocks and feature components. |
| `webapp/hooks` | React hooks for API and toast behavior. |
| `webapp/lib` | API client and utility functions. |
| `webapp/types` | Shared TypeScript types. |

## Docs Ownership

Use `docs/` for canonical onboarding, architecture, operations, and API docs. Keep local READMEs near optional stacks when they are command-specific, but link back to `docs/README.md`.

## Tests

Current test areas:

- `tests/ingestion/unit`
- `tests/ingestion/integration`
- `tests/retrieval/unit`
- `tests/retrieval/integration`
- `tests/test_retrieval_api.py`

Run:

```bash
pytest
```

Some integration tests may require Qdrant, catalog data, or environment variables.
