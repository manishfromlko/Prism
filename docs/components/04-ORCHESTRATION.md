# Orchestration

## Local Manual Orchestration

Manual execution is the source of truth for development:

```bash
python -m src.ingestion.cli --root dataset --mode incremental
python -m src.retrieval.indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode incremental
python -m src.retrieval.artifact_summary_indexer --catalog dataset/.ingestion/ingestion_catalog.json --mode incremental
curl -X POST http://localhost:8000/admin/sync-profiles-from-summaries
curl -X POST http://localhost:8000/admin/ingest-docs
```

## FastAPI Admin Orchestration

The backend exposes admin endpoints for runtime refreshes:

| Endpoint | Purpose |
| --- | --- |
| `POST /admin/sync` | Run artifact vector indexing. Body: `{"force_full": true}` for full mode. |
| `POST /admin/sync-artifact-summaries?force_full=true` | Generate and index artifact summaries. |
| `POST /admin/sync-profiles` | Generate user profiles from raw catalog content. |
| `POST /admin/sync-profiles-from-summaries` | Generate user profiles from artifact summaries. |
| `POST /admin/ingest-docs?drop_existing=true` | Re-ingest `platform_documents/*.docx`. |

Batch work is executed in a background thread from the request handler, then service objects are refreshed where needed.

## Airflow

Files:

- `airflow/dags/ingestion_dag.py`
- `docker-compose.airflow.yml`
- `airflow/README.md`

The current DAG is named `kubeflow_workspace_ingestion` and runs daily. It executes:

```bash
PYTHONPATH=/opt/airflow/repo python -m src.ingestion.cli \
  --root /opt/airflow/repo/dataset \
  --mode incremental
```

The DAG only runs ingestion. If you need a fully refreshed semantic system, add downstream indexing, summary, and profile tasks.

```mermaid
flowchart LR
    schedule["Daily Airflow schedule"] --> ingest["ingestion CLI incremental"]
    ingest --> catalog["Catalog refreshed"]
    catalog -. missing today .-> index["Add vector indexing task"]
    index -. optional .-> summaries["Add summary indexing task"]
    summaries -. optional .-> profiles["Add profile task"]
```

## Databricks

Files:

- `databricks/README.md`
- `databricks/jobs/01_ingest_artifacts.py`
- `databricks/jobs/02_generate_summaries.py`
- `databricks/jobs/03_generate_user_profiles.py`
- `databricks/jobs/04_sync_vector_indexes.py`
- `databricks/adapters/`
- `databricks/app.yaml`

The Databricks path replaces local components:

| Local | Databricks |
| --- | --- |
| Milvus | Databricks Vector Search |
| Filesystem `dataset/` | Unity Catalog volumes |
| JSON/Milvus batch outputs | Delta tables and Vector Search indexes |
| LiteLLM/OpenAI direct calls | Databricks Model Serving endpoints |
| Airflow/manual scripts | Databricks Workflows |
| FastAPI container | Databricks Apps |

Treat the Databricks docs as a migration guide, not a requirement for local development.
