# API

Interactive docs are available at:

```text
http://localhost:8000/docs
```

Important endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend, vector store, and embedding health. |
| `GET` | `/metrics` | Runtime metrics for dashboard cards. |
| `POST` | `/query` | Semantic artifact search. |
| `GET` | `/workspaces` | List workspaces from Postgres metadata. |
| `GET` | `/workspaces/{id}` | Get workspace details. |
| `GET` | `/user-profiles` | List generated user profiles. |
| `GET` | `/user-profiles/{id}` | Get one generated user profile. |
| `POST` | `/chat` | Multi-agent chat endpoint with session memory. |
| `POST` | `/admin/sync` | Incremental backend sync. |
| `POST` | `/admin/sync-profiles-from-summaries` | Incrementally upsert profiles from summaries. |
| `POST` | `/admin/ingest-docs` | Ingest `data/platform_documents/*.docx` into `platform_docs`. |
