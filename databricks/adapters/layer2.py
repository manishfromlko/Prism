"""
Drop-in replacement for src/observability/layer2.py in a Databricks environment.

Changes from the original:
  - LLM backend: Databricks Model Serving instead of LiteLLM → OpenAI
  - Score sink:  mlflow.log_metrics() instead of Langfuse score_trace()
  - No lf.flush() needed (no Langfuse SDK)

Everything else is identical: daemon thread, asyncio.run() in thread, RAGAS 0.4.3,
sequential metric execution, exact_match → LLM judge path.
"""

import asyncio
import logging
import os
import threading
from typing import Dict, List, Optional

import mlflow

from .scoring import score_trace

logger = logging.getLogger(__name__)

_EVAL_MODEL  = os.getenv("EVAL_MODEL",  "databricks-meta-llama-3-1-405b-instruct")
_JUDGE_MODEL = os.getenv("JUDGE_MODEL", "databricks-meta-llama-3-1-405b-instruct")

try:
    from ragas.llms import llm_factory
    from ragas.embeddings import OpenAIEmbeddings
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecisionWithoutReference,
        Faithfulness,
    )
    _RAGAS_AVAILABLE = True
except ImportError:
    _RAGAS_AVAILABLE = False


def _make_ragas_components():
    from openai import AsyncOpenAI
    host  = os.environ["DATABRICKS_HOST"].rstrip("/")
    token = os.environ["DATABRICKS_TOKEN"]
    client = AsyncOpenAI(api_key=token, base_url=f"{host}/serving-endpoints")
    llm = llm_factory(_EVAL_MODEL, client=client)
    emb = OpenAIEmbeddings(client=client, model="databricks-bge-large-en")
    return llm, emb


def _make_sync_client():
    from openai import OpenAI
    host  = os.environ["DATABRICKS_HOST"].rstrip("/")
    token = os.environ["DATABRICKS_TOKEN"]
    return OpenAI(api_key=token, base_url=f"{host}/serving-endpoints")


def _extract_contexts(doc_hits, artifact_hits, user_hits) -> List[str]:
    ctx: List[str] = []
    for h in doc_hits:
        if h.get("chunk_text"):       ctx.append(h["chunk_text"])
    for h in artifact_hits:
        if h.get("artifact_summary"): ctx.append(h["artifact_summary"])
    for h in user_hits:
        if h.get("user_profile"):     ctx.append(h["user_profile"])
    return ctx


async def _run_ragas_eval(trace_id, query, answer, contexts, llm, emb):
    if not contexts:
        logger.debug(f"[layer2] No contexts for trace {trace_id}, skipping RAGAS")
        return

    metrics = [
        ("faithfulness",      Faithfulness(llm=llm),                    {"retrieved_contexts": contexts}),
        ("answer_relevancy",  AnswerRelevancy(llm=llm, embeddings=emb), {}),
        ("context_precision", ContextPrecisionWithoutReference(llm=llm), {"retrieved_contexts": contexts}),
    ]
    for name, metric, extra in metrics:
        try:
            result = await metric.ascore(user_input=query, response=answer, **extra)
            value = float(result.value)
            mlflow.log_metric(name, round(value, 4))
            logger.debug(f"[layer2] {name}={value:.4f} trace={trace_id}")
        except Exception as e:
            logger.warning(f"[layer2] RAGAS {name} failed trace={trace_id}: {e}")


def _run_llm_judge(trace_id, query, answer):
    client = _make_sync_client()
    prompt = (
        "You are an impartial evaluator. Rate how well the user profile below answers the question.\n\n"
        f"Question: {query}\n\nProfile:\n{answer}\n\n"
        "Scoring criteria:\n"
        "  1.0 — profile directly and completely answers the question\n"
        "  0.7 — profile is about the right person but only partially answers\n"
        "  0.3 — profile is loosely related but mostly irrelevant\n"
        "  0.0 — profile has nothing to do with the question\n\n"
        "Reply with a single decimal number only. No explanation."
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
        logger.debug(f"[layer2] profile_relevance={value:.4f} trace={trace_id}")
    except Exception as e:
        logger.warning(f"[layer2] LLM judge failed trace={trace_id}: {e}")


def _background_eval(trace_id, query, answer, intent, doc_hits, artifact_hits, user_hits, exact_match):
    try:
        if exact_match:
            _run_llm_judge(trace_id, query, answer)
        elif _RAGAS_AVAILABLE:
            llm, emb = _make_ragas_components()
            if llm is not None:
                contexts = _extract_contexts(doc_hits, artifact_hits, user_hits)
                asyncio.run(_run_ragas_eval(trace_id, query, answer, contexts, llm, emb))
        else:
            logger.debug("[layer2] ragas not installed, skipping")
    except Exception as e:
        logger.warning(f"[layer2] Background eval crashed trace={trace_id}: {e}")


def evaluate_in_background(
    trace_id: str,
    query: str,
    answer: str,
    intent: str,
    doc_hits: Optional[List[Dict]] = None,
    artifact_hits: Optional[List[Dict]] = None,
    user_hits: Optional[List[Dict]] = None,
    exact_match: bool = False,
) -> None:
    """Fire-and-forget Layer 2 quality evaluation in a daemon thread."""
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
    logger.debug(f"[layer2] eval dispatched trace={trace_id} intent={intent} exact={exact_match}")
