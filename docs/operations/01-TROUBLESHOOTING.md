# Troubleshooting

## Backend Fails on Startup

Check:

```bash
docker ps
curl http://localhost:8000/health
```

Common causes:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Milvus connection error | Milvus is not running or wrong host/port | `docker compose up -d milvus`; verify `MILVUS_HOST=127.0.0.1`, `MILVUS_PORT=19530`. |
| Embedding errors | Missing or invalid OpenAI credentials | Set `OPENAI_API_KEY`. |
| Catalog warning | `dataset/.ingestion/ingestion_catalog.json` missing | Run ingestion. |
| Chat engine not ready | Missing docs/summaries/profiles collections | Run summary, profile, and doc ingestion steps. |

## Search Returns No Results

Confirm the artifact collection has entities:

```bash
curl http://localhost:8000/health
```

Then rebuild:

```bash
python -m src.ingestion.cli --root dataset --mode full
python -m src.retrieval.indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode full
```

## Chat Returns 503

The chatbot requires:

- `artifact_summaries`
- `user_profiles`
- `platform_docs`
- embedding service

Run:

```bash
python -m src.retrieval.artifact_summary_indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode full
curl -X POST http://localhost:8000/admin/sync-profiles-from-summaries
curl -X POST http://localhost:8000/admin/ingest-docs
```

Restart the backend if stores were created while the app was down.

## Webapp Says Backend Unavailable

Check the Python backend:

```bash
curl http://localhost:8000/health
```

Start the webapp with:

```bash
cd webapp
PYTHON_API_URL=http://localhost:8000 npm run dev
```

Remember: browser calls go to Next.js `/api/*`; Next.js route handlers call `PYTHON_API_URL`.

## Milvus Dimension Mismatch

If inserts fail with vector dimension errors, make sure these match:

```bash
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

If the collection was created with a different dimension, rebuild it:

```bash
python -m src.retrieval.indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode full
python -m src.retrieval.artifact_summary_indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode full
```

You may also need to drop/recreate profile and docs collections through their full refresh paths.

## LiteLLM or Langfuse Issues

If chatbot LLM calls fail, verify `LITELLM_BASE_URL` and the LiteLLM container:

```bash
cd rag-observability/litellm
docker compose ps
```

For local runs without LiteLLM, either start the proxy or point `LITELLM_BASE_URL` at a compatible OpenAI-style endpoint.

## Airflow Runs But Search Is Stale

The current Airflow DAG only runs ingestion. Add downstream tasks or manually run:

```bash
python -m src.retrieval.indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode incremental
python -m src.retrieval.artifact_summary_indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode incremental
curl -X POST http://localhost:8000/admin/sync-profiles-from-summaries
```
