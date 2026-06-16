# API Reference

Base URL for local FastAPI:

```text
http://localhost:8000
```

Interactive OpenAPI docs:

```text
http://localhost:8000/docs
```

## System

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | API name/version. |
| `GET` | `/health` | Vector store, embedding service, and cache health. |
| `GET` | `/metrics` | JSON app metrics: uptime, query count, average query time, error rate, memory. |

## Workspaces

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/workspaces` | List workspaces from the ingestion catalog. |
| `GET` | `/workspaces/{workspace_id}` | Get one workspace. |
| `GET` | `/profile/workspace/{workspace_id}` | Compute profiling insights for one workspace. |

## Search

`POST /query`

Request:

```json
{
  "query": "PySpark examples",
  "top_k": 10,
  "workspace_ids": null,
  "use_hybrid": false
}
```

Response:

```json
{
  "results": [
    {
      "artifact_id": "user:file.ipynb",
      "content": "text chunk",
      "metadata": {},
      "score": 0.82
    }
  ],
  "total_found": 1,
  "query_time_ms": 120.0,
  "query": "PySpark examples"
}
```

## Artifact Summaries

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/artifact-summaries?workspace_id=<id>&artifact_id=<id>` | Get one artifact summary. |
| `GET` | `/artifact-summaries/workspace/{workspace_id}` | List summaries for one workspace/user. |
| `POST` | `/admin/sync-artifact-summaries?force_full=true` | Generate and index summaries. |

## User Profiles

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/user-profiles` | List all user profiles. |
| `GET` | `/user-profiles/{user_id}` | Get one user profile. |
| `POST` | `/admin/sync-profiles` | Generate profiles from raw catalog content. |
| `POST` | `/admin/sync-profiles-from-summaries` | Generate profiles from artifact summaries. |

## Chat

`POST /chat`

Request:

```json
{
  "query": "Who works on NLP?",
  "history": [],
  "session_id": "optional-session"
}
```

Response:

```json
{
  "answer": "...",
  "intent": "USER_SEARCH",
  "confidence": 0.9,
  "exact_match": false,
  "artifacts": [],
  "users": [],
  "sources": [],
  "trace_id": "uuid"
}
```

Possible intents:

- `DOC_QA`
- `ARTIFACT_SEARCH`
- `USER_SEARCH`
- `HYBRID`
- `OUT_OF_SCOPE`

## Admin

| Method | Path | Body/query | Purpose |
| --- | --- | --- | --- |
| `POST` | `/admin/sync` | `{"force_full": false}` | Re-index artifact vectors. |
| `POST` | `/admin/ingest-docs` | `?drop_existing=true` | Ingest `platform_documents/*.docx`. |
| `POST` | `/admin/sync-artifact-summaries` | `?force_full=true` | Generate/index artifact summaries. |
| `POST` | `/admin/sync-profiles-from-summaries` | none | Generate/index user profiles from summaries. |

## Observability

`POST /observability/score`

```json
{
  "trace_id": "uuid",
  "score_name": "faithfulness",
  "value": 0.8,
  "comment": "optional"
}
```

`POST /observability/feedback`

```json
{
  "trace_id": "uuid",
  "thumbs_up": true
}
```

## Webapp Proxy Routes

The Next.js app exposes browser-facing routes under `/api/*` and forwards them to FastAPI.

| Web route | FastAPI route |
| --- | --- |
| `POST /api/search` | `POST /query` |
| `POST /api/chat` | `POST /chat` |
| `GET /api/health` | `GET /health` |
| `GET /api/metrics` | `GET /metrics` |
| `GET /api/workspaces` | `GET /workspaces` |
| `GET /api/workspaces/[id]` | `GET /workspaces/{id}` |
| `GET /api/workspaces/[id]/profile` | `GET /profile/workspace/{id}` |
| `GET /api/user-profiles` | `GET /user-profiles` |
| `GET /api/user-profiles/[id]` | `GET /user-profiles/{id}` |
| `GET /api/artifact-summaries` | `GET /artifact-summaries` |
| `GET /api/artifact-summaries/workspace/[id]` | `GET /artifact-summaries/workspace/{id}` |
| `POST /api/admin/sync` | `POST /admin/sync` |
| `POST /api/admin/ingest-docs` | `POST /admin/ingest-docs` |
| `POST /api/admin/sync-profiles-from-summaries` | `POST /admin/sync-profiles-from-summaries` |
