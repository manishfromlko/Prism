# First Run

This is the end-to-end local runbook for a new machine.

## 1. Start Qdrant

```bash
docker compose up -d qdrant
```

Wait a few seconds, then confirm the container is running:

```bash
docker ps
```

## 2. Create the Ingestion Catalog

```bash
python -m src.ingestion.cli --root dataset --mode full
```

Expected output is quiet on success. The important artifacts are:

- `dataset/.ingestion/ingestion_catalog.json`
- `dataset/.ingestion/ingestion_audit.json`

Use incremental mode after the first run:

```bash
python -m src.ingestion.cli --root dataset --mode incremental
```

## 3. Index Artifacts for Search

```bash
python -m src.retrieval.indexer \
  --catalog dataset/.ingestion/ingestion_catalog.json \
  --mode full
```

This populates the Qdrant collection named by `QDRANT_COLLECTION`, defaulting to `kubeflow_artifacts`.

## 4. Generate Artifact Summaries

```bash
python -m src.retrieval.artifact_summary_indexer \
  --catalog dataset/.ingestion/ingestion_catalog.json \
  --mode full
```

This creates or updates the `artifact_summaries` Qdrant collection.

## 5. Start the FastAPI Backend

```bash
python -m uvicorn src.retrieval.api:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

API docs:

```text
http://localhost:8000/docs
```

## 6. Generate User Profiles

Run this after the backend is up and artifact summaries exist:

```bash
curl -X POST http://localhost:8000/admin/sync-profiles-from-summaries
```

This populates `user_profiles`.

## 7. Ingest Platform Documents for Chat

The chatbot answers platform documentation questions from Word documents in `platform_documents/`.

```bash
curl -X POST http://localhost:8000/admin/ingest-docs
```

Use this after changing docs:

```bash
curl -X POST "http://localhost:8000/admin/ingest-docs?drop_existing=true"
```

This populates `platform_docs`.

## 8. Smoke Test Backend Features

Search:

```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"PySpark notebook","top_k":3}' | jq
```

Workspaces:

```bash
curl -s http://localhost:8000/workspaces | jq
```

Chat:

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"How do I submit a Spark job?"}' | jq
```

If chat returns `503`, one of `platform_docs`, `artifact_summaries`, or `user_profiles` is not ready.

## 9. Start the Webapp

In a new terminal:

```bash
cd webapp
PYTHON_API_URL=http://localhost:8000 npm run dev
```

Open:

```text
http://localhost:3000
```

## 10. Common Daily Commands

Refresh changed artifacts:

```bash
python -m src.ingestion.cli --root dataset --mode incremental
python -m src.retrieval.indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode incremental
python -m src.retrieval.artifact_summary_indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode incremental
curl -X POST http://localhost:8000/admin/sync-profiles-from-summaries
```

Fully rebuild search data:

```bash
python -m src.ingestion.cli --root dataset --mode full
python -m src.retrieval.indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode full
python -m src.retrieval.artifact_summary_indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode full
curl -X POST http://localhost:8000/admin/sync-profiles-from-summaries
curl -X POST "http://localhost:8000/admin/ingest-docs?drop_existing=true"
```
