# Ingestion

Ingestion is incremental by default for normal development. Use full mode only when rebuilding Qdrant from scratch.

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
- Catalog: `data/workspaces/.ingestion/ingestion_catalog.json`
- Platform docs: `data/platform_documents/*.docx`

The large local legacy `ravi.verma` workspace is intentionally ignored in this branch. The tracked sample workspaces are small enough for Git and cover similar user-name disambiguation cases.

