# RAG Observability Overview

End-to-end observability for this pipeline is split across four layers.
Each layer uses a standard OSS tool with a clear, non-overlapping scope.

---

## Layer 1 — LLM Calls: LiteLLM + Langfuse

**What it covers:** every outbound LLM API call (OpenAI, etc.)

**Signals:**
- Token usage and cost per request and model
- Prompt and response traces (full input/output logging)
- Latency breakdown (time-to-first-token, total)
- Error rates and retries

**How it works:**
LiteLLM acts as a unified proxy/router in front of OpenAI. A single callback registration sends all traces to Langfuse automatically — no manual instrumentation per call site.

```python
import litellm
litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]
```

**Langfuse concepts to know:**
- **Trace** — one user request end-to-end
- **Span** — individual steps within a trace (classify, retrieve, generate)
- **Score** — eval metrics attached to a trace (e.g. RAGAS faithfulness)

---

## Layer 2 — RAG Quality Evaluation: RAGAS

**What it covers:** the quality of retrieval and generation, not just latency

**Signals (the three core metrics):**

| Metric | Question answered | How computed |
|---|---|---|
| **Context Relevance** | Are the retrieved chunks actually relevant to the query? | LLM judges each chunk against the question |
| **Faithfulness** | Does the answer stay grounded in the retrieved context? | LLM checks if every claim in the answer is supported |
| **Answer Relevance** | Does the answer address what the user asked? | Embedding similarity between question and answer |

**Usage pattern — offline batch eval:**
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_relevancy
from datasets import Dataset

# Build an eval dataset from sampled production queries
data = {
    "question": [...],
    "answer": [...],        # LLM output
    "contexts": [...],      # retrieved chunks passed to LLM
    "ground_truth": [...],  # optional reference answer
}
result = evaluate(Dataset.from_dict(data), metrics=[faithfulness, answer_relevancy, context_relevancy])
```

**Langfuse integration:** RAGAS scores can be posted back to Langfuse traces so quality metrics and LLM traces live in one place.

**Why this matters:** latency and cost metrics tell you nothing about whether the RAG pipeline is actually returning correct, grounded answers. RAGAS is the only layer that measures that.

---

## Layer 3 — Application + Vector DB Metrics: Prometheus + Grafana

**What it covers:** infrastructure health — FastAPI request metrics and Milvus retrieval metrics.

### FastAPI instrumentation

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

Exposes at `/metrics`:
- `http_request_duration_seconds` — latency by endpoint and status code
- `http_requests_total` — throughput and error rate
- `http_request_size_bytes` / `http_response_size_bytes`

### Milvus instrumentation

Milvus ships a built-in Prometheus exporter. Enable it in `milvus.yaml`:
```yaml
metrics:
  enabled: true
  port: 9091
```

Key Milvus metrics:
- `milvus_query_latency_ms` — vector search latency
- `milvus_search_request_count` — search QPS
- `milvus_cache_hit_rate` — index cache efficiency
- `milvus_num_entities` — collection size over time

### Grafana dashboards

Point Grafana at the Prometheus datasource and build two dashboards:

1. **API dashboard** — request rate, P50/P95/P99 latency, error rate per endpoint
2. **Retrieval dashboard** — Milvus search latency, QPS, cache hit rate, collection growth

Milvus provides an official Grafana dashboard JSON that can be imported directly.

---

## Layer 4 — Embedding & Query Drift: Evidently

**What it covers:** detecting when incoming queries drift away from the distribution the system was built on.

**Why it matters:** retrieval quality degrades silently when user query patterns shift. A vector index built on one distribution of queries will return poor results for a shifted distribution — and no latency metric will catch this.

**Signals:**
- Embedding distribution drift (cosine similarity distribution over time)
- Text feature drift (query length, vocabulary, topic distribution)
- Retrieval score distribution drift (are similarity scores trending lower?)

**Usage pattern:**
```python
from evidently.report import Report
from evidently.metric_preset import TextOverviewPreset, DataDriftPreset

report = Report(metrics=[DataDriftPreset(), TextOverviewPreset()])
report.run(reference_data=baseline_queries_df, current_data=recent_queries_df)
report.save_html("drift_report.html")
```

Run this as a scheduled job (daily or weekly) against a sliding window of production query logs.

---

## Architecture: How All Four Layers Connect

```
Incoming Request
       │
       ▼
  FastAPI ──────────────────────────► Prometheus ──► Grafana
       │                              (request metrics)   (dashboards)
       │
       ├──► IntentClassifier (LiteLLM) ──► Langfuse
       │                                    (LLM traces)
       ├──► QueryRewriter   (LiteLLM) ──► Langfuse
       │
       ├──► Milvus Search ────────────► Prometheus ──► Grafana
       │                              (retrieval metrics)
       │
       └──► LLM Generate   (LiteLLM) ──► Langfuse
                                          │
                                          └──► RAGAS scores
                                               (offline batch eval)

Query logs ──► Evidently ──► Drift reports (scheduled)
```

---

## Implementation Priority

| Priority | Tool | Effort | What it unlocks |
|---|---|---|---|
| 1 | **LiteLLM + Langfuse** | Low — single callback | Full LLM cost and trace visibility |
| 2 | **RAGAS** | Medium — need eval dataset | Measures actual RAG quality |
| 3 | **Prometheus + Grafana** | Low — instrumentator + config | Infra health, SLA monitoring |
| 4 | **Evidently** | Medium — scheduled job | Early warning for retrieval degradation |

---

## Key Interview Talking Points

- **Separation of concerns:** each tool owns one layer — no overlap, no gaps
- **RAGAS is the differentiator:** most teams instrument latency and cost; few measure faithfulness and context relevance — this is what separates LLMOps from plain observability
- **Langfuse as the correlation layer:** LLM traces + RAGAS scores in one place means you can correlate "this query cost $0.002 and had faithfulness=0.4" — actionable signal for prompt/retrieval tuning
- **Evidently closes the feedback loop:** production query drift → triggers re-evaluation → drives re-indexing or prompt updates
- **Milvus + Prometheus:** retrieval is a first-class citizen in the monitoring stack, not an afterthought
