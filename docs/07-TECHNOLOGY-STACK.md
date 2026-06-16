# Technology Stack

## Backend

| Technology | Used for | Where |
| --- | --- | --- |
| Python 3.11+ | Backend, ingestion, indexing, evaluation | `src/`, `tests/`, `evaluation/` |
| FastAPI | HTTP API | `src/retrieval/api.py` |
| Uvicorn | Local ASGI server | First-run commands |
| Pydantic | API/config models | `src/retrieval/api.py`, `src/retrieval/config.py` |
| LangChain document model | Retrieval document abstraction | `src/retrieval/document_loader.py`, retrievers |
| OpenAI SDK | Embeddings and OpenAI-compatible chat calls | `src/retrieval/embeddings.py`, chatbot |
| python-dotenv | Local `.env` loading | `src/retrieval/config.py` |
| python-docx | Platform document ingestion | `src/retrieval/chatbot/doc_ingestion.py` |
| RapidFuzz | User name matching | `src/retrieval/chatbot/user_resolver.py` |

## Storage and Search

| Technology | Used for |
| --- | --- |
| Milvus | Vector database for artifact chunks, summaries, user profiles, and platform docs |
| JSON files | Ingestion catalog and audit log |
| HNSW index | Approximate nearest-neighbor search |
| Cosine similarity | Default vector distance metric |

## Frontend

| Technology | Used for |
| --- | --- |
| Next.js 15 | Web application and API route proxy layer |
| React 18 | UI rendering |
| TypeScript | Frontend type safety |
| Tailwind CSS | Styling |
| Radix UI / shadcn-style components | Base UI primitives |
| TanStack Query | Client data fetching/cache |
| Recharts | Charts and analytics |
| Lucide React | Icons |

## Observability and Evaluation

| Technology | Used for |
| --- | --- |
| LiteLLM | OpenAI-compatible proxy and trace callback layer |
| Langfuse | LLM traces, scores, feedback |
| RAGAS | Retrieval/generation quality evaluation patterns |
| Prometheus/Grafana | Optional infrastructure metrics |
| Evidently | Optional drift detection |

## Orchestration and Deployment

| Technology | Used for |
| --- | --- |
| Docker Compose | Local Milvus, backend, webapp, and optional observability stacks |
| Airflow | Optional scheduled ingestion |
| Databricks | Optional cloud-native migration target |
| Databricks Vector Search | Databricks replacement for Milvus |
| Databricks Model Serving | Databricks replacement for OpenAI/LiteLLM endpoint management |

## Dependency Files

| File | Purpose |
| --- | --- |
| `requirements.txt` | Explicit Python dependencies for local backend and tests |
| `pyproject.toml` | Minimal project metadata and some Python dependencies for `uv` |
| `uv.lock` | Locked Python dependency graph |
| `webapp/package.json` | Frontend scripts and dependencies |
| `webapp/package-lock.json` | Locked Node dependency graph |
| `docker-compose.yml` | Local Milvus/backend/webapp services |
| `docker-compose.airflow.yml` | Optional Airflow stack |

## Version Notes

- Use `EMBEDDING_DIMENSION=1536` with `text-embedding-3-small`.
- Keep the Milvus schema dimension and embedding model dimension in sync.
- The current local code expects an OpenAI-compatible embedding service. Older compose defaults that mention `sentence-transformers/all-MiniLM-L6-v2` should be reviewed before use.
