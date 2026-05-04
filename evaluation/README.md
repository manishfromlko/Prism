# Chatbot Evaluation Dataset

End-to-end test dataset for the Kubeflow Workspace Intelligence chatbot. Covers all five intents, all retrieval paths, both scoring layers, and edge cases. Use it to validate Langfuse traces and score distributions after any change to the engine, prompts, or retrieval stack.

---

## Dataset File

`chatbot_eval_dataset.json` — 31 labelled queries with expected intents, expected Langfuse trace structure, expected score ranges, and step-by-step verification instructions.

---

## Intent Types and Coverage

| Intent | Queries | What it tests |
|--------|---------|---------------|
| `DOC_QA` | 6 | Questions answered from platform docs (Kubeflow guides) |
| `ARTIFACT_SEARCH` | 7 | Finding notebooks/scripts by technology, task, or concept |
| `USER_SEARCH` | 8 | Exact name lookup, fuzzy name, expertise-based semantic search |
| `HYBRID` | 4 | Queries spanning two or three intent types simultaneously |
| `OUT_OF_SCOPE` | 6 | Off-topic queries that must short-circuit immediately |
| Edge cases | 6 | Multi-turn context, nonsense input, long queries, intent boundaries, user feedback |

---

## How the Pipeline Works Per Intent

```
User Query
    │
    ▼
[classify]  LLM call — always runs
    │
    ├─ OUT_OF_SCOPE ──────────────────────────────► Return hardcoded reply
    │                                                 (no further LLM calls, no scores)
    │
    ▼
[rewrite]  LLM call — enriches query for better vector recall
    │
    ├─ USER_SEARCH (name found via RapidFuzz)
    │       │
    │       ▼
    │   [user_resolve]  LLM disambiguation
    │       │
    │       ├─ exact_uid found ──────────────────► Return raw Milvus profile
    │       │                                       Layer 2: profile_relevance (LLM judge)
    │       │                                       No Layer 1 scores
    │       │
    │       └─ ambiguous ────────────────────────► Return LLM disambiguation answer
    │                                               No scores at all
    │
    └─ DOC_QA / ARTIFACT_SEARCH / semantic USER_SEARCH / HYBRID
            │
            ▼
        [vector retrieve]  Milvus similarity search
            │  DOC_QA:          doc_store       top-5 chunks
            │  ARTIFACT_SEARCH: artifact_store  top-5 summaries
            │  USER_SEARCH:     user_store       top-5 profiles
            │  HYBRID:          all 3 stores     top-3 each
            │
            ▼
        [generate]  LLM call — gpt-4o-mini, T=0.2, max 600 tokens
            │
            ▼
        [score Layer 1]  Inline, ~0ms — 4 heuristic scores posted to Langfuse
            │
            ▼
        [evaluate Layer 2]  Background thread, 10–30s — RAGAS or LLM judge
```

---

## Scoring Mechanism

### Layer 1 — Heuristic Scores (inline, always synchronous)

Posted immediately after every `generate` response. No LLM call. Appear in Langfuse within 1–2 seconds.

| Score | How calculated | What it indicates |
|-------|---------------|-------------------|
| `response_length` | Normalized answer char count. Peak 1.0 at 300–2000 chars. Penalises very short (<50) or very long (>2000). | Answer is neither a one-liner nor a wall of text |
| `has_content` | 1.0 if answer text contains no fallback phrases; 0.0 if it does | LLM found useful context, not a "couldn't find" response |
| `intent_confidence` | Classifier confidence passed through as-is (0–1) | How certain the router was about the query type |
| `source_count` | `retrieved_sources / 5`, capped at 1.0 | Retrieval coverage — how many sources contributed |

> **Not posted for:** `OUT_OF_SCOPE` (engine short-circuits before scoring), exact `USER_SEARCH` match (early return before scoring).

### Layer 2 — RAGAS Scores (background thread, ~10–30s delay)

Run asynchronously in a daemon thread after the response is returned. Uses `gpt-4o` as the eval model (stronger than the generation model). Appear in Langfuse 10–30 seconds after the trace.

| Score | Applies to | What it measures |
|-------|-----------|-----------------|
| `faithfulness` | DOC_QA, ARTIFACT_SEARCH, semantic USER_SEARCH, HYBRID | Answer is grounded in retrieved context, not hallucinated |
| `answer_relevancy` | Same as above | Answer addresses the actual question asked |
| `context_precision` | Same as above | Top-ranked retrieved chunks are the most relevant ones |
| `profile_relevance` | Exact `USER_SEARCH` name match only | LLM judge (0 / 0.3 / 0.7 / 1.0): does the profile answer the question? |

### User-Initiated Scores

| Score | Source | Value |
|-------|--------|-------|
| `user_feedback` | Frontend thumbs-up / thumbs-down | 1.0 = positive, 0.0 = negative |

---

## Score Health Thresholds

| Score | Green | Amber | Red |
|-------|-------|-------|-----|
| `faithfulness` | > 0.70 | 0.50–0.70 | < 0.50 |
| `answer_relevancy` | > 0.75 | 0.60–0.75 | < 0.60 |
| `context_precision` | > 0.65 | 0.45–0.65 | < 0.45 |
| `intent_confidence` | > 0.80 | 0.60–0.80 | < 0.60 |
| `has_content` | 1.0 | — | 0.0 |
| `source_count` | > 0.40 | 0.20–0.40 | 0.0 |
| `profile_relevance` | ≥ 0.70 | 0.30 | 0.0 |

---

## How to Run

### Option A — Frontend (manual, easiest)

1. Start the stack: backend on `http://localhost:8000`, frontend on `http://localhost:3002`, Langfuse on `http://localhost:3001`.
2. Open `http://localhost:3002` in a browser.
3. Submit each query from the dataset.
4. Note the `trace_id` returned in the response (visible in browser devtools → Network → `/chat` response body).
5. Open Langfuse and look up the trace by ID.

### Option B — API (scripted)

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I submit a Spark job in Kubeflow?", "session_id": "eval-run-001"}' \
  | jq '{intent: .intent, confidence: .confidence, trace_id: .trace_id}'
```

### Option C — Batch runner script

```python
import json, requests, time

dataset = json.load(open("chatbot_eval_dataset.json"))
results = []

for q in dataset["queries"]:
    resp = requests.post("http://localhost:8000/chat", json={
        "query": q["query"],
        "session_id": "eval-batch-001"
    })
    data = resp.json()
    results.append({
        "id": q["id"],
        "query": q["query"],
        "expected_intent": q["expected"]["intent"],
        "actual_intent": data.get("intent"),
        "confidence": data.get("confidence"),
        "trace_id": data.get("trace_id"),
        "passed": data.get("intent") == q["expected"]["intent"]
    })
    time.sleep(1)  # avoid rate-limiting LiteLLM

passed = sum(1 for r in results if r["passed"])
print(f"Intent classification: {passed}/{len(results)} correct")
for r in results:
    status = "✓" if r["passed"] else "✗"
    print(f"  {status} [{r['id']}] expected={r['expected_intent']} got={r['actual_intent']} conf={r['confidence']:.2f}")
```

---

## How to Read Results in Langfuse

### Finding a Trace

1. Open `http://localhost:3001` → **Traces** tab.
2. Filter by **Tag** → `intent:DOC_QA` (or any intent).
3. Filter by **Trace Name** → `chat · DOC_QA`.
4. Click any trace row to open it.

### What to Check Inside a Trace

| Panel | What to look for |
|-------|-----------------|
| **Generation spans** | Should see `classify`, `rewrite`, `generate` in sequence. `OUT_OF_SCOPE` has only `classify`. Exact `USER_SEARCH` has `classify`, `rewrite`, `user_resolve`. |
| **Scores tab** | Layer 1 scores appear within 1–2s. RAGAS scores appear 10–30s later. |
| **Metadata (generate span)** | `query`, `search_query`, `intent`, `confidence`, `doc_hits`, `artifact_hits`, `user_hits`, `source_count` |
| **Input (generate span)** | Full prompt sent to LLM — verify retrieved context matches expected sources |
| **Output (generate span)** | LLM answer — spot-check for hallucinated artifact IDs or user names |

### Key Diagnostic Patterns

| Pattern | What it means | Action |
|---------|--------------|--------|
| `has_content=0` + `source_count=0` | Query matched nothing — correct for missing-content tests | Add docs or re-index |
| `has_content=1` + `faithfulness<0.4` | LLM answered from training data, not retrieved context | Hallucination — strengthen system prompt grounding instruction |
| `intent_confidence<0.6` | Classifier uncertain — boundary query | Review classifier system prompt |
| `OUT_OF_SCOPE` trace has any scores | Engine short-circuit is broken | Check `engine.py` early-return logic |
| Exact `USER_SEARCH` has Layer 1 scores | Early-return is not triggering | Check `exact_uid` resolution path in `engine.py` |
| `profile_relevance=0.0` on exact name lookup | Wrong user was resolved or profile is empty | Re-run user profile indexer |
| RAGAS scores never appear | Background thread crashed | Check backend logs for `[layer2]` error lines |

---

## Key Invariants to Assert

These must hold on every run. If any fail, something is broken:

1. **`OUT_OF_SCOPE` traces have exactly 1 generation span (`classify`) and 0 scores.**
2. **Exact `USER_SEARCH` traces have no `generate` span and no Layer 1 scores.**
3. **All non-OUT_OF_SCOPE traces have a `rewrite` span.**
4. **`has_content=0` traces never contain fabricated artifact IDs or user names in the answer.**
5. **`source_count > 0` for any trace where the answer is substantive.**
6. **`faithfulness` and `answer_relevancy` appear on every `generate`-path trace within 60 seconds.**

---

## Dataset Entry Structure (reference)

```json
{
  "id": "DOC-001",
  "category": "doc_qa_how_to",
  "query": "...",
  "expected": {
    "intent": "DOC_QA",
    "confidence_range": "high",
    "min_confidence": 0.85
  },
  "pipeline": {
    "llm_calls": ["classify", "rewrite", "generate"],
    "retrievers_used": ["doc_store"],
    "expected_hits": { "doc_hits": 3, "artifact_hits": 0, "user_hits": 0 }
  },
  "langfuse": {
    "trace_name": "chat · DOC_QA",
    "tags": ["intent:DOC_QA"],
    "scores_expected": { ... },
    "scores_not_expected": [...],
    "verification_steps": [...]
  },
  "notes": "..."
}
```
