# Layer 2 Observability — Testing Guide

Layer 2 runs RAGAS evaluation (faithfulness, answer_relevancy, context_precision) in a background
thread after each response. For USER_SEARCH exact-match hits it uses an LLM judge instead
(profile_relevance). Scores are posted to Langfuse via the Python SDK and attached to the same
trace that LiteLLM created for the request.

---

## Prerequisites

All three services must be running before any test:

```bash
# 1. Langfuse  (http://localhost:3001)
cd rag-observability/langfuse && docker compose up -d

# 2. LiteLLM proxy  (http://localhost:4000)
cd rag-observability/litellm && docker compose up -d

# 3. Milvus  (host 192.168.1.10:19530 per .env)
#    Start however your local Milvus runs (Docker or standalone)

# Activate virtualenv
source .venv/bin/activate
```

Check `.env` has these set:

```
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=sk-1234
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3001
```

---

## Test 1 — Unit: verify RAGAS components initialise

Checks that the async LLM + embedding wrappers can reach LiteLLM and produce scores.
Does **not** require Langfuse or Milvus.

```bash
python - <<'EOF'
import asyncio, os, sys
from dotenv import load_dotenv
load_dotenv(".env")
sys.path.insert(0, "src")

from observability.layer2 import _make_ragas_components, _run_ragas_eval

llm, emb = _make_ragas_components()
print(f"LLM is_async={llm.is_async}  Emb is_async={emb.is_async}")

contexts = [
    "KubeFlow is a platform for running ML workflows on Kubernetes. "
    "It supports Pipelines, Notebooks, and Model Serving components."
]

async def run():
    await _run_ragas_eval(
        trace_id="unit-test-001",
        query="What is KubeFlow used for?",
        answer="KubeFlow is used to run machine learning workflows on Kubernetes.",
        contexts=contexts,
        llm=llm,
        emb=emb,
    )

asyncio.run(run())
print("Done — check logs above for faithfulness / answer_relevancy / context_precision values")
EOF
```

**Expected output** (values will vary slightly):

```
LLM is_async=True  Emb is_async=True
[layer2] faithfulness=1.0000 trace=unit-test-001
[layer2] answer_relevancy=0.95xx trace=unit-test-001
[layer2] context_precision=1.0000 trace=unit-test-001
Done
```

> Note: `Score queued` lines will appear but scores won't land in Langfuse because
> `unit-test-001` is not a real trace. That's fine — this test only validates RAGAS execution.

---

## Test 2 — Unit: LLM-as-judge (USER_SEARCH exact match)

```bash
python - <<'EOF'
import os, sys
from dotenv import load_dotenv
load_dotenv(".env")
sys.path.insert(0, "src")

from observability.layer2 import _run_llm_judge

_run_llm_judge(
    trace_id="unit-test-002",
    query="Who works on NLP and deep learning?",
    answer="**alex.chen**\n\nAlex Chen is a senior ML engineer specialising in NLP and deep learning. "
           "Current projects: transformer fine-tuning pipeline, multilingual embeddings.",
)
print("Done — check logs for profile_relevance score")
EOF
```

**Expected output:**

```
[layer2] profile_relevance=0.9x trace=unit-test-002
```

---

## Test 3 — Integration: end-to-end via the FastAPI server

This test goes through the full pipeline so scores land on a real Langfuse trace.

### 3a. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

### 3b. Send a DOC_QA request

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I submit a Spark job on the platform?"}' \
  | python3 -m json.tool
```

Copy the `trace_id` from the response JSON.

### 3c. Wait ~30–60 seconds for the background thread to finish

RAGAS makes 3–4 LLM calls per request (statement extraction, NLI, question generation, embedding).
On a cold LiteLLM proxy allow up to 60 s.

### 3d. Check scores in Langfuse

1. Open **http://localhost:3001**
2. Log in (`admin@example.com` / `admin123`)
3. Navigate to **Traces**
4. Find the trace by the `trace_id` from the response (or by timestamp)
5. Open the trace detail — scroll down to the **Scores** section

You should see 7 scores total on the trace:

| Score name | Source | Expected range |
|---|---|---|
| `response_length` | Layer 1 heuristic | 0 – 1 |
| `has_content` | Layer 1 heuristic | 0 or 1 |
| `intent_confidence` | Layer 1 heuristic | 0 – 1 |
| `source_count` | Layer 1 heuristic | 0 – 1 |
| `faithfulness` | Layer 2 RAGAS | 0 – 1 |
| `answer_relevancy` | Layer 2 RAGAS | 0 – 1 |
| `context_precision` | Layer 2 RAGAS | 0 – 1 |

### 3e. Test USER_SEARCH exact match (profile_relevance)

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about Alex Chen"}' \
  | python3 -m json.tool
```

If the user is resolved by name (exact match), the response will include `"exact_match": true`.
After ~10 s you should see `profile_relevance` (from the LLM judge) on that trace instead of
the RAGAS scores.

---

## Test 4 — Verify scores land in Langfuse (curl)

You can confirm a score exists via the Langfuse API directly:

```bash
TRACE_ID="<paste trace_id here>"
curl -s \
  -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  "http://localhost:3001/api/public/scores?traceId=$TRACE_ID" \
  | python3 -m json.tool
```

Look for objects with `"name": "faithfulness"`, `"name": "answer_relevancy"`, etc.
Each has a `"value"` field and `"comment": "ragas"`.

---

## Are the scores visible in Langfuse?

**Yes — with one condition:** the trace must already exist in Langfuse before the SDK posts
the score. In practice:

- LiteLLM creates the trace synchronously when the `/chat/completions` call completes.
- RAGAS runs ~5–60 s later in a background thread and posts scores to that trace_id.
- Langfuse attaches them to the existing trace. They appear in the Scores tab.

**If scores don't appear:**

1. Check the FastAPI server logs for `[layer2]` lines:
   - `eval dispatched` → thread started OK
   - `faithfulness=x.xxxx` → RAGAS ran and score was queued
   - `RAGAS faithfulness failed` → check the error message

2. Check that `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` in `.env` match what Langfuse
   shows under **Settings → API Keys**.

3. Confirm LiteLLM can reach Langfuse from inside Docker:
   ```bash
   docker exec litellm-litellm-1 curl -s http://host.docker.internal:3001/api/public/health
   ```

4. Check the Langfuse SDK is flushing — `lf.flush()` is called after every RAGAS batch.
   If the process exits before flush completes (e.g. in a script), scores may be dropped.
   In the server this is not an issue since the process stays alive.

---

## Score interpretation

| Score | What a low value means | What a high value means |
|---|---|---|
| `faithfulness` | Answer contains claims not in the retrieved docs | Answer stays within what was retrieved |
| `answer_relevancy` | Answer drifts from the question | Answer directly addresses the question |
| `context_precision` | Retrieved chunks were not useful for this answer | Retrieved chunks were directly relevant |
| `profile_relevance` | Returned profile doesn't match what was asked | Profile squarely answers the user query |

A consistently low `faithfulness` with high `answer_relevancy` usually means the model is
answering from its own knowledge rather than the retrieved context — a hallucination signal.
A low `context_precision` usually means the retriever is returning low-quality chunks.
