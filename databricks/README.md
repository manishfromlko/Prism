# Kubeflow Workspace Intelligence — Databricks Migration Guide

Replicates the full Kubeflow Workspace Intelligence chatbot stack on Databricks, replacing every self-hosted component with a Databricks-native equivalent and swapping Langfuse observability for MLflow Tracing.

---

## Component Mapping

| Current (self-hosted) | Databricks Equivalent |
|-----------------------|----------------------|
| Milvus (3 collections) | Databricks Vector Search (3 indexes backed by Delta tables) |
| LiteLLM proxy (port 4000) | Databricks Model Serving (external model endpoints for `gpt-4o-mini` and `text-embedding-3-small`) |
| OpenAI text-embedding-3-small | Databricks Model Serving endpoint `text-embedding-3-small` |
| gpt-4o-mini (classify / rewrite / generate) | Databricks Model Serving endpoint `gpt-4o-mini` |
| gpt-4o (RAGAS eval / LLM judge) | Databricks Model Serving endpoint `gpt-4o-mini` |
| Langfuse (traces + scores) | MLflow Tracing (MLflow ≥ 2.14, built into Databricks Runtime 15.4+) |
| FastAPI on Docker | Databricks Apps |
| Next.js webapp | Databricks Apps (separate app) |
| NAS mount | Unity Catalog Volumes |
| Airflow / local cron ingestion | Databricks Workflows (Jobs) |
| `.env` config | Databricks Secrets (secret scopes) |

---

## Prerequisites

1. Databricks workspace on AWS/Azure/GCP with **Unity Catalog enabled**.
2. **Databricks Runtime 15.4 LTS ML** or later (ships MLflow 2.16, Python 3.11).
3. A Unity Catalog **catalog** and **schema** you own (example names used below: `kubeflow.intelligence`).
4. A **Vector Search endpoint** created in the workspace (one endpoint can host all 3 indexes).
5. Two **Model Serving endpoints** already registered: `gpt-4o-mini` (chat) and `text-embedding-3-small` (embeddings).
6. Personal access token (PAT) or service principal stored in a **Databricks secret scope**.

---

## Step 1 — Unity Catalog Setup

Run the following in a Databricks notebook once.

```sql
-- Create catalog and schema
CREATE CATALOG IF NOT EXISTS kubeflow;
CREATE SCHEMA  IF NOT EXISTS kubeflow.intelligence;

-- Unity Catalog volume for raw artifact files (replaces NAS mount)
CREATE VOLUME IF NOT EXISTS kubeflow.intelligence.workspace_files
  COMMENT 'Raw notebooks and scripts ingested from Kubeflow workspaces';
```

Upload your workspace artifacts to the volume:

```bash
# From your local machine using the Databricks CLI
databricks fs cp --recursive ./dataset/workspaces \
  dbfs:/Volumes/kubeflow/intelligence/workspace_files/
```

---

## Step 2 — Delta Tables as Vector Search Sources

Vector Search indexes in Databricks are backed by a **source Delta table** (one row per chunk or document). Create one table per collection.

```python
# Run in a Databricks notebook
spark.sql("""
  CREATE TABLE IF NOT EXISTS kubeflow.intelligence.artifact_chunks (
    chunk_id     STRING NOT NULL,
    artifact_id  STRING NOT NULL,
    chunk_text   STRING,
    chunk_index  INT,
    file_path    STRING,
    file_type    STRING,
    sha256_hash  STRING
  )
  USING DELTA
  TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")

spark.sql("""
  CREATE TABLE IF NOT EXISTS kubeflow.intelligence.artifact_summaries (
    artifact_id       STRING NOT NULL,
    artifact_summary  STRING,
    artifact_type     STRING,
    file_path         STRING
  )
  USING DELTA
  TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")

spark.sql("""
  CREATE TABLE IF NOT EXISTS kubeflow.intelligence.user_profiles (
    user_id       STRING NOT NULL,
    user_profile  STRING,
    display_name  STRING
  )
  USING DELTA
  TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
""")
```

> `delta.enableChangeDataFeed = true` is **required** — Vector Search uses it to detect row-level changes and sync indexes incrementally.
>
> **Note:** Vector Search does not support `MAP`, `STRUCT`, or `ARRAY` column types. Drop them from the source table or cast to `STRING` (JSON) before syncing. The `metadata` column has been removed — add individual `STRING` columns if you need filterable fields (e.g. `workspace_id STRING`, `language STRING`).

---

## Step 3 — Vector Search Endpoint and Indexes

### 3a. Create the endpoint (UI or SDK)

```python
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

# One endpoint serves all three indexes
vsc.create_endpoint(
    name="kubeflow-intelligence-endpoint",
    endpoint_type="STANDARD",
)
```

### 3b. Create indexes (Delta Sync, managed embeddings)

Using **managed embeddings** means Databricks calls the embedding model automatically on every Delta table sync — no separate embedding job needed.

Create all three indexes now — it is fine to create them against empty tables. The index metadata is registered immediately; embeddings are generated on the first `.sync()` call, which happens at the end of the ingestion workflow (Step 7). **Do not call `.sync()` here.**

```python
# Artifact chunks index
vsc.create_delta_sync_index(
    endpoint_name="kubeflow-intelligence-endpoint",
    index_name="kubeflow.intelligence.artifact_chunks_index",
    source_table_name="kubeflow.intelligence.artifact_chunks",
    pipeline_type="TRIGGERED",            # CONTINUOUS for real-time; TRIGGERED for batch
    primary_key="chunk_id",
    embedding_source_column="chunk_text",
    embedding_model_endpoint_name="text-embedding-3-small",
)

# Artifact summaries index
vsc.create_delta_sync_index(
    endpoint_name="kubeflow-intelligence-endpoint",
    index_name="kubeflow.intelligence.artifact_summaries_index",
    source_table_name="kubeflow.intelligence.artifact_summaries",
    pipeline_type="TRIGGERED",
    primary_key="artifact_id",
    embedding_source_column="artifact_summary",
    embedding_model_endpoint_name="text-embedding-3-small",
)

# User profiles index
vsc.create_delta_sync_index(
    endpoint_name="kubeflow-intelligence-endpoint",
    index_name="kubeflow.intelligence.user_profiles_index",
    source_table_name="kubeflow.intelligence.user_profiles",
    pipeline_type="TRIGGERED",
    primary_key="user_id",
    embedding_source_column="user_profile",
    embedding_model_endpoint_name="text-embedding-3-small",
)
```

After this step, indexes exist but are empty. Proceed to Steps 4–6, then run the ingestion workflow in Step 7. Task 4 of the workflow (`04_sync_vector_indexes.py`) will call `.sync()` on all three indexes once data is in the Delta tables.

---

## Step 4 — Model Serving (LLM Endpoints)

Both models are already registered in your Databricks Model Serving workspace. No extra setup needed here.

| Role | Endpoint name |
|------|--------------|
| Classify / rewrite / generate | `gpt-4o-mini` |
| RAGAS eval + LLM judge | `gpt-4o-mini` |
| Embeddings (Vector Search + RAGAS) | `text-embedding-3-small` |

The adapters call these via the standard OpenAI-compatible API that Databricks exposes on every Model Serving endpoint:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DATABRICKS_TOKEN"],
    base_url=f"{os.environ['DATABRICKS_HOST']}/serving-endpoints",
)

# Chat — hits your registered gpt-4o-mini endpoint
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
)

# Embeddings — hits your registered text-embedding-3-small endpoint
emb = client.embeddings.create(
    model="text-embedding-3-small",
    input=["some text"],
)
```

> **Verify endpoints are healthy** before running the ingestion workflow:
> ```bash
> databricks serving-endpoints get --name gpt-4o-mini
> databricks serving-endpoints get --name text-embedding-3-small
> ```

---

## Step 5 — Secrets Setup

```bash
# Create a secret scope
databricks secrets create-scope kubeflow-scope

# Store credentials
databricks secrets put-secret kubeflow-scope databricks-host   --string-value "https://<workspace>.azuredatabricks.net"
databricks secrets put-secret kubeflow-scope databricks-token  --string-value "<pat-or-sp-token>"
```

---

## Step 6 — Observability: MLflow Tracing (replaces Langfuse + LiteLLM)

MLflow Tracing is the Databricks-native equivalent of Langfuse. It records spans, inputs/outputs, token counts, and custom scores — all stored in the MLflow experiment attached to your workspace.

### 6a. What maps to what

| Langfuse / LiteLLM concept | MLflow Tracing equivalent |
|---------------------------|--------------------------|
| `trace_id` (UUID) | `mlflow.get_current_active_span().request_id` |
| LiteLLM metadata forwarding | `mlflow.start_span(name="classify")` context manager |
| `classify` generation span | `@mlflow.trace(name="classify", span_type="LLM")` |
| `rewrite` generation span | `@mlflow.trace(name="rewrite", span_type="LLM")` |
| `generate` generation span | `@mlflow.trace(name="generate", span_type="LLM")` |
| `user_resolve` span | `@mlflow.trace(name="user_resolve", span_type="LLM")` |
| Root trace metadata (intent, confidence) | `mlflow.update_current_trace(tags={...})` |
| `score_trace()` → Langfuse score | `mlflow.log_metric()` or `client.set_trace_tag()` |
| Langfuse session grouping | `mlflow.set_experiment_tags({"session_id": ...})` |
| Layer 1 scores | `mlflow.log_metrics({...})` inside the root trace |
| RAGAS Layer 2 scores | same, posted from the daemon thread |

### 6b. Replace `src/observability/llm_client.py`

```python
# databricks/adapters/llm_client.py
import os
from openai import OpenAI

def make_llm_client() -> OpenAI:
    host  = os.getenv("DATABRICKS_HOST", "").rstrip("/")
    token = os.getenv("DATABRICKS_TOKEN", "")
    return OpenAI(
        api_key=token,
        base_url=f"{host}/serving-endpoints",
    )

def litellm_metadata(trace_id: str, generation_name: str, **kwargs) -> dict:
    # No-op: span grouping is handled by MLflow context managers, not HTTP headers
    return {}
```

### 6c. Replace `src/observability/scoring.py`

```python
# databricks/adapters/scoring.py
import mlflow
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def score_trace(trace_id: str, name: str, value: float, comment: Optional[str] = None) -> None:
    """Post a named score as an MLflow metric on the active trace."""
    try:
        with mlflow.start_span(name=f"score_{name}", span_type="UNKNOWN") as span:
            span.set_inputs({"trace_id": trace_id, "score_name": name})
            span.set_outputs({"value": round(float(value), 4)})
        # Also log as a run metric so it appears in the Experiment UI
        mlflow.log_metric(name, round(float(value), 4))
        logger.debug(f"Score logged: {name}={value:.4f} trace={trace_id}")
    except Exception as e:
        logger.warning(f"Failed to log score '{name}': {e}")

def score_user_feedback(trace_id: str, thumbs_up: bool) -> None:
    mlflow.set_experiment_tag(f"user_feedback_{trace_id}", "thumbs_up" if thumbs_up else "thumbs_down")
    score_trace(trace_id, "user_feedback", 1.0 if thumbs_up else 0.0)

def score_response_quality(
    trace_id: str, answer: str, intent: str,
    confidence: float = 0.0, source_count: int = 0,
) -> None:
    n = len(answer.strip())
    if n < 50:
        length_score = n / 50 * 0.5
    elif n <= 300:
        length_score = 0.5 + (n - 50) / 250 * 0.5
    elif n <= 2000:
        length_score = 1.0
    else:
        length_score = max(0.5, 1.0 - (n - 2000) / 2000 * 0.3)

    _FALLBACK = ["i couldn't find", "i don't have access", "please try again",
                 "outside what i can help", "no matching", "i encountered an error"]
    has_content = 0.0 if any(p in answer.lower() for p in _FALLBACK) else 1.0
    src_score = min(1.0, source_count / 5) if source_count > 0 else 0.0

    mlflow.log_metrics({
        "response_length":   round(length_score, 4),
        "has_content":       has_content,
        "intent_confidence": round(min(1.0, float(confidence)), 4),
        "source_count":      round(src_score, 4),
    })
```

### 6d. Replace `src/observability/layer2.py` (RAGAS with MLflow)

```python
# databricks/adapters/layer2.py
import asyncio
import logging
import os
import threading
from typing import Dict, List, Optional

import mlflow
from ragas.llms import llm_factory
from ragas.embeddings import OpenAIEmbeddings
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecisionWithoutReference,
    Faithfulness,
)

from .llm_client import make_llm_client
from .scoring import score_trace

logger = logging.getLogger(__name__)

_EVAL_MODEL  = os.getenv("EVAL_MODEL",  "gpt-4o-mini")
_JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4o-mini")


def _make_ragas_components():
    from openai import AsyncOpenAI
    host  = os.getenv("DATABRICKS_HOST", "").rstrip("/")
    token = os.getenv("DATABRICKS_TOKEN", "")
    client = AsyncOpenAI(
        api_key=token,
        base_url=f"{host}/serving-endpoints",
    )
    llm = llm_factory(_EVAL_MODEL, client=client)
    emb = OpenAIEmbeddings(client=client, model="text-embedding-3-small")
    return llm, emb


def _extract_contexts(doc_hits, artifact_hits, user_hits) -> List[str]:
    ctx = []
    for h in doc_hits:
        if h.get("chunk_text"):       ctx.append(h["chunk_text"])
    for h in artifact_hits:
        if h.get("artifact_summary"): ctx.append(h["artifact_summary"])
    for h in user_hits:
        if h.get("user_profile"):     ctx.append(h["user_profile"])
    return ctx


async def _run_ragas_eval(trace_id, query, answer, contexts, llm, emb):
    if not contexts:
        return
    metrics = [
        ("faithfulness",      Faithfulness(llm=llm),                    {"retrieved_contexts": contexts}),
        ("answer_relevancy",  AnswerRelevancy(llm=llm, embeddings=emb), {}),
        ("context_precision", ContextPrecisionWithoutReference(llm=llm), {"retrieved_contexts": contexts}),
    ]
    scores = {}
    for name, metric, extra in metrics:
        try:
            result = await metric.ascore(user_input=query, response=answer, **extra)
            scores[name] = round(float(result.value), 4)
        except Exception as e:
            logger.warning(f"[layer2] RAGAS {name} failed: {e}")
    if scores:
        mlflow.log_metrics(scores)


def _run_llm_judge(trace_id, query, answer):
    client = make_llm_client()
    prompt = (
        "You are an impartial evaluator. Rate how well the user profile below answers the question.\n\n"
        f"Question: {query}\n\nProfile:\n{answer}\n\n"
        "Scoring: 1.0=complete 0.7=partial 0.3=loosely related 0.0=irrelevant\n"
        "Reply with a single decimal only."
    )
    try:
        resp = client.chat.completions.create(
            model=_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )
        value = max(0.0, min(1.0, float(resp.choices[0].message.content.strip())))
        mlflow.log_metric("profile_relevance", round(value, 4))
    except Exception as e:
        logger.warning(f"[layer2] LLM judge failed: {e}")


def _background_eval(trace_id, query, answer, intent, doc_hits, artifact_hits, user_hits, exact_match):
    try:
        if exact_match:
            _run_llm_judge(trace_id, query, answer)
        else:
            llm, emb = _make_ragas_components()
            if llm:
                contexts = _extract_contexts(doc_hits, artifact_hits, user_hits)
                asyncio.run(_run_ragas_eval(trace_id, query, answer, contexts, llm, emb))
    except Exception as e:
        logger.warning(f"[layer2] Background eval crashed: {e}")


def evaluate_in_background(trace_id, query, answer, intent,
                            doc_hits=None, artifact_hits=None, user_hits=None,
                            exact_match=False):
    if not trace_id or not answer:
        return
    t = threading.Thread(
        target=_background_eval,
        args=(trace_id, query, answer, intent,
              doc_hits or [], artifact_hits or [], user_hits or [], exact_match),
        daemon=True,
        name=f"layer2-{trace_id[:8]}",
    )
    t.start()
```

### 6e. Wrap the chat engine with an MLflow trace

In `engine.py`, replace the LiteLLM metadata pattern with MLflow context managers:

```python
import mlflow

def chat(self, query: str, history=None, session_id=None):
    with mlflow.start_span(name="chat", span_type="CHAIN") as root_span:
        trace_id = root_span.request_id   # MLflow assigns the ID
        root_span.set_inputs({"query": query, "session_id": session_id})

        # Classify
        with mlflow.start_span(name="classify", span_type="LLM") as span:
            classification = self.classifier.classify(query)
            span.set_outputs(classification)

        intent = classification["intent"]
        confidence = classification["confidence"]

        if intent == "OUT_OF_SCOPE":
            root_span.set_outputs({"intent": "OUT_OF_SCOPE"})
            return format_response(answer=_OUT_OF_SCOPE_REPLY, ...)

        # Rewrite
        with mlflow.start_span(name="rewrite", span_type="LLM") as span:
            search_query = self.rewriter.rewrite(query)
            span.set_outputs({"search_query": search_query})

        # ... retrieve, generate as before ...

        # Enrich root trace
        mlflow.update_current_trace(tags={
            "intent": intent,
            "session_id": session_id or "",
        })
        root_span.set_outputs({"answer": answer, "intent": intent})
```

---

## Step 7 — Ingestion Pipeline as a Databricks Workflow

Replace the local ingestion CLI with a **Databricks Job** (multi-task workflow).

### Notebook: `databricks/jobs/01_ingest_artifacts.py`

```python
# Databricks notebook — Task 1: scan volumes, extract, embed, write Delta
import os
from databricks.sdk.runtime import dbutils

# Mount credentials from secrets
os.environ["DATABRICKS_HOST"]  = dbutils.secrets.get("kubeflow-scope", "databricks-host")
os.environ["DATABRICKS_TOKEN"] = dbutils.secrets.get("kubeflow-scope", "databricks-token")

VOLUME_PATH = "/Volumes/kubeflow/intelligence/workspace_files"

# Walk volume, extract text, write to Delta (reuses existing extractors/guards logic)
from src.ingestion.extractors import extract_artifact
from src.ingestion.guards import DocumentGuard

rows = []
for root, dirs, files in os.walk(VOLUME_PATH):
    for fname in files:
        path = os.path.join(root, fname)
        artifact = extract_artifact(path)
        if artifact and DocumentGuard.is_safe(artifact):
            rows.append(artifact.to_dict())

df = spark.createDataFrame(rows)
df.write.mode("append").saveAsTable("kubeflow.intelligence.artifact_chunks")
print(f"Wrote {df.count()} rows to artifact_chunks")
```

### Notebook: `databricks/jobs/02_generate_summaries.py`

```python
# Task 2: generate LLM summaries for new/updated artifacts
import os
from databricks.sdk.runtime import dbutils

os.environ["DATABRICKS_HOST"]  = dbutils.secrets.get("kubeflow-scope", "databricks-host")
os.environ["DATABRICKS_TOKEN"] = dbutils.secrets.get("kubeflow-scope", "databricks-token")

from src.retrieval.artifact_summary_generator import ArtifactSummaryGenerator

# Read only rows without a summary yet
new_artifacts = spark.sql("""
    SELECT a.artifact_id, a.chunk_text, a.file_type
    FROM kubeflow.intelligence.artifact_chunks a
    LEFT JOIN kubeflow.intelligence.artifact_summaries s
      ON a.artifact_id = s.artifact_id
    WHERE s.artifact_id IS NULL
""").collect()

gen = ArtifactSummaryGenerator()
rows = []
for row in new_artifacts:
    summary = gen.generate(row.chunk_text, row.file_type)
    rows.append({"artifact_id": row.artifact_id, "artifact_summary": summary,
                 "artifact_type": row.file_type})

if rows:
    df = spark.createDataFrame(rows)
    df.write.mode("append").saveAsTable("kubeflow.intelligence.artifact_summaries")
    print(f"Generated {len(rows)} summaries")
```

### Notebook: `databricks/jobs/03_generate_user_profiles.py`

```python
# Task 3: generate or refresh user profiles from summaries
import os
from databricks.sdk.runtime import dbutils

os.environ["DATABRICKS_HOST"]  = dbutils.secrets.get("kubeflow-scope", "databricks-host")
os.environ["DATABRICKS_TOKEN"] = dbutils.secrets.get("kubeflow-scope", "databricks-token")

from src.retrieval.user_profile_from_summaries_generator import UserProfileFromSummariesGenerator

summaries_by_user = spark.sql("""
    SELECT artifact_id, artifact_summary,
           split(artifact_id, '/')[0] AS user_id
    FROM kubeflow.intelligence.artifact_summaries
""").groupBy("user_id").agg({"artifact_summary": "collect_list"}).collect()

gen = UserProfileFromSummariesGenerator()
rows = []
for row in summaries_by_user:
    profile = gen.generate(row.user_id, row["collect_list(artifact_summary)"])
    rows.append({"user_id": row.user_id, "user_profile": profile})

df = spark.createDataFrame(rows)
df.write.mode("overwrite").saveAsTable("kubeflow.intelligence.user_profiles")
print(f"Wrote {len(rows)} user profiles")
```

### Notebook: `databricks/jobs/04_sync_vector_indexes.py`

```python
# Task 4: trigger Vector Search index sync after Delta tables are updated
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()
ENDPOINT = "kubeflow-intelligence-endpoint"

for index_name in [
    "kubeflow.intelligence.artifact_chunks_index",
    "kubeflow.intelligence.artifact_summaries_index",
    "kubeflow.intelligence.user_profiles_index",
]:
    vsc.get_index(ENDPOINT, index_name).sync()
    print(f"Sync triggered: {index_name}")
```

### Workflow definition (JSON, import via UI or CLI)

```json
{
  "name": "kubeflow-intelligence-ingestion",
  "schedule": { "quartz_cron_expression": "0 0 2 * * ?", "timezone_id": "UTC" },
  "tasks": [
    { "task_key": "ingest",          "notebook_task": { "notebook_path": "/databricks/jobs/01_ingest_artifacts" },    "depends_on": [] },
    { "task_key": "summaries",       "notebook_task": { "notebook_path": "/databricks/jobs/02_generate_summaries" },  "depends_on": [{"task_key": "ingest"}] },
    { "task_key": "user_profiles",   "notebook_task": { "notebook_path": "/databricks/jobs/03_generate_user_profiles" }, "depends_on": [{"task_key": "summaries"}] },
    { "task_key": "vector_sync",     "notebook_task": { "notebook_path": "/databricks/jobs/04_sync_vector_indexes" }, "depends_on": [{"task_key": "user_profiles"}] }
  ]
}
```

---

## Step 8 — Replace `VectorStore` (Milvus → Databricks Vector Search)

```python
# databricks/adapters/vector_store.py
import os
from typing import Any, Dict, List, Optional
from databricks.vector_search.client import VectorSearchClient

ENDPOINT = os.getenv("VECTOR_SEARCH_ENDPOINT", "kubeflow-intelligence-endpoint")

class DatabricksVectorStore:
    def __init__(self, index_name: str):
        vsc = VectorSearchClient(
            workspace_url=os.environ["DATABRICKS_HOST"],
            personal_access_token=os.environ["DATABRICKS_TOKEN"],
        )
        self.index = vsc.get_index(ENDPOINT, index_name)

    def search(
        self,
        query_text: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        results = self.index.similarity_search(
            query_text=query_text,   # managed embeddings — pass text, not vector
            columns=["*"],
            num_results=top_k,
            filters=filters,
        )
        return results.get("result", {}).get("data_array", [])
```

Use `DatabricksVectorStore("kubeflow.intelligence.artifact_chunks_index")` wherever the code currently uses `VectorStore(config)`.

---

## Step 9 — Databricks Apps (FastAPI backend)

Databricks Apps runs FastAPI natively. No Docker needed.

1. In the Databricks workspace UI → **Apps** → **Create App** → choose **FastAPI**.
2. Point it at `src/retrieval/api.py` as the entry module.
3. Set environment variables from secrets in the App config:

```yaml
# app.yaml (Databricks Apps config)
command: ["uvicorn", "src.retrieval.api:app", "--host", "0.0.0.0", "--port", "8000"]
env:
  - name: DATABRICKS_HOST
    valueFrom:
      secretKeyRef: { scope: kubeflow-scope, key: databricks-host }
  - name: DATABRICKS_TOKEN
    valueFrom:
      secretKeyRef: { scope: kubeflow-scope, key: databricks-token }
  - name: VECTOR_SEARCH_ENDPOINT
    value: "kubeflow-intelligence-endpoint"
  - name: EVAL_MODEL
    value: "gpt-4o-mini"
  - name: JUDGE_MODEL
    value: "gpt-4o-mini"
```

---

## Step 10 — MLflow Experiment Setup

Every chat request will log a trace into a shared MLflow experiment.

```python
import mlflow

mlflow.set_tracking_uri("databricks")   # uses workspace MLflow automatically
mlflow.set_experiment("/kubeflow-intelligence/chatbot")
mlflow.enable_system_metrics_logging()
```

Add this to the FastAPI startup handler in `api.py`.

### Viewing Traces in the UI

1. Open **Experiments** → `/kubeflow-intelligence/chatbot`.
2. Switch to the **Traces** tab.
3. Click any trace row — you see the `classify → rewrite → generate` span tree, inputs/outputs, and metrics.
4. Filter by tag `intent:DOC_QA` or session ID.

### Trace Structure in MLflow

```
chat  [CHAIN span, root]
├── classify      [LLM span]   → intent, confidence
├── rewrite       [LLM span]   → search_query
├── user_resolve  [LLM span]   → only for ambiguous USER_SEARCH
└── generate      [LLM span]   → answer text
    metrics:
      response_length, has_content, intent_confidence, source_count   ← Layer 1
      faithfulness, answer_relevancy, context_precision               ← Layer 2 (async)
      profile_relevance                                               ← Layer 2 (exact match only)
```

---

## Environment Variables Reference

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABRICKS_HOST` | `https://<workspace>.azuredatabricks.net` | From secret scope |
| `DATABRICKS_TOKEN` | PAT or SP token | From secret scope |
| `VECTOR_SEARCH_ENDPOINT` | `kubeflow-intelligence-endpoint` | Created in Step 3 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Used by managed embeddings |
| `LLM_MODEL` | `gpt-4o-mini` | classify / rewrite / generate |
| `EVAL_MODEL` | `gpt-4o-mini` | RAGAS eval |
| `JUDGE_MODEL` | `gpt-4o-mini` | profile_relevance LLM judge |
| `MLFLOW_EXPERIMENT` | `/kubeflow-intelligence/chatbot` | MLflow experiment path |

---

## Files in This Folder

```
databricks/
├── README.md                       ← this file
├── adapters/
│   ├── llm_client.py               ← replaces src/observability/llm_client.py
│   ├── scoring.py                  ← replaces src/observability/scoring.py
│   ├── layer2.py                   ← replaces src/observability/layer2.py
│   └── vector_store.py             ← replaces src/retrieval/vector_store.py
├── jobs/
│   ├── 01_ingest_artifacts.py      ← Databricks Workflow Task 1
│   ├── 02_generate_summaries.py    ← Databricks Workflow Task 2
│   ├── 03_generate_user_profiles.py← Databricks Workflow Task 3
│   └── 04_sync_vector_indexes.py   ← Databricks Workflow Task 4
└── app.yaml                        ← Databricks Apps config
```

---

## What Does NOT Change

- All five intent types and their routing logic (`engine.py`) — unchanged.
- Prompt templates in `prompts/` — unchanged.
- `UserNameResolver` / RapidFuzz name matching — unchanged.
- Layer 1 heuristic scoring logic (length, has_content, source_count) — only the sink changes (MLflow instead of Langfuse).
- RAGAS metrics (`Faithfulness`, `AnswerRelevancy`, `ContextPrecisionWithoutReference`) — unchanged; only the LLM backend and score sink change.
- The `user_feedback` thumbs-up/thumbs-down endpoint — posts to MLflow instead of Langfuse, otherwise identical.
- The Next.js frontend — no changes required; it calls the same `/chat` and `/observability/feedback` endpoints.

---

## Score Health Thresholds (same as original)

| Score | Green | Amber | Red |
|-------|-------|-------|-----|
| `faithfulness` | > 0.70 | 0.50–0.70 | < 0.50 |
| `answer_relevancy` | > 0.75 | 0.60–0.75 | < 0.60 |
| `context_precision` | > 0.65 | 0.45–0.65 | < 0.45 |
| `intent_confidence` | > 0.80 | 0.60–0.80 | < 0.60 |
| `has_content` | 1.0 | — | 0.0 |
| `source_count` | > 0.40 | 0.20–0.40 | 0.0 |
| `profile_relevance` | ≥ 0.70 | 0.30 | 0.0 |

Set these as alerts in MLflow using the **Metric Threshold** feature on the experiment dashboard.
