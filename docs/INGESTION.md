# Ingestion

Ingestion is incremental by default for normal development. Use full mode only when rebuilding Postgres metadata and Qdrant from scratch.

## Incremental Pipeline

```bash
docker compose exec backend python -m src.ingestion.cli --root /app/data/workspaces --mode incremental
docker compose exec backend python -m src.retrieval.indexer --mode incremental
docker compose exec backend python -m src.retrieval.artifact_summary_indexer --mode incremental
docker compose exec backend python -m src.retrieval.profile_from_summaries_indexer --mode incremental
docker compose exec backend python -m src.retrieval.chatbot.doc_ingestion
```

## Full Rebuild

```bash
docker compose exec backend python -m src.ingestion.cli --root /app/data/workspaces --mode full
docker compose exec backend python -m src.retrieval.indexer --mode full
docker compose exec backend python -m src.retrieval.artifact_summary_indexer --mode full
docker compose exec backend python -m src.retrieval.profile_from_summaries_indexer --mode full
docker compose exec backend python -m src.retrieval.chatbot.doc_ingestion
```

## Data Sources

- Workspace source: `data/workspaces/`
- Metadata source of truth: Postgres `workspaces`, `artifacts`, and `ingestion_audits` tables
- Platform docs: `data/platform_documents/*.docx`

Git tracks only five small seed workspaces so the repository stays light. Local runtime is broader: ingestion scans every workspace directory that exists under `data/workspaces/`, including ignored local-only folders copied in for testing.

If you add more local workspaces, run the incremental or full pipeline again so Postgres metadata and Qdrant collections reflect those folders. Those extra workspace folders stay ignored by Git unless you explicitly change `.gitignore`.

To recreate only the five Git-tracked seed workspaces:

```bash
python scripts/download_public_workspaces.py
```

To download every known public workspace locally without adding them to Git:

```bash
python scripts/download_public_workspaces.py --all
```
