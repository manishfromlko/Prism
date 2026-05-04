"""
Layer 2 observability — RAGAS-based RAG quality evaluation.

Runs asynchronously in a daemon thread after the response is returned to the
caller, so it never adds latency to the API response.

Scores posted per request (RAGAS 0.4.3):
  faithfulness        — answer grounded in retrieved contexts (0–1)
  answer_relevancy    — answer relevant to the question (0–1)
  context_precision   — context ranked by relevance (0–1)

For USER_SEARCH exact-match (profile lookup, no LLM generation):
  profile_relevance   — LLM judge: does the profile answer the query (0–1)

All functions are no-ops if LITELLM_BASE_URL is unset or ragas is missing.
"""

import asyncio
import logging
import os
import threading
from typing import Dict, List, Optional

from .scoring import _get_langfuse, score_trace

logger = logging.getLogger(__name__)

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


# ── shared helpers ────────────────────────────────────────────────────────────

def _make_sync_client():
    from openai import OpenAI
    base_url = os.getenv("LITELLM_BASE_URL", "")
    api_key = os.getenv("LITELLM_API_KEY", "sk-1234")
    if not base_url:
        return None
    return OpenAI(api_key=api_key, base_url=base_url)


_EVAL_MODEL = "gpt-4o"  # stronger than the generation model for reliable metric scores


def _make_ragas_components():
    from openai import AsyncOpenAI
    base_url = os.getenv("LITELLM_BASE_URL", "")
    api_key = os.getenv("LITELLM_API_KEY", "sk-1234")
    if not base_url:
        return None, None
    # Both LLM and embeddings wrappers need an AsyncOpenAI client so that
    # RAGAS can call agenerate() / aembed_text() inside ascore()
    async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    llm = llm_factory(_EVAL_MODEL, client=async_client)
    emb = OpenAIEmbeddings(client=async_client, model="text-embedding-3-small")
    return llm, emb


def _extract_contexts(
    doc_hits: List[Dict],
    artifact_hits: List[Dict],
    user_hits: List[Dict],
) -> List[str]:
    contexts: List[str] = []
    for h in doc_hits:
        if h.get("chunk_text"):
            contexts.append(h["chunk_text"])
    for h in artifact_hits:
        if h.get("artifact_summary"):
            contexts.append(h["artifact_summary"])
    for h in user_hits:
        if h.get("user_profile"):
            contexts.append(h["user_profile"])
    return contexts


# ── RAGAS eval ────────────────────────────────────────────────────────────────

async def _run_ragas_eval(
    trace_id: str,
    query: str,
    answer: str,
    contexts: List[str],
    llm,
    emb,
) -> None:
    if not contexts:
        logger.debug(f"[layer2] No contexts for trace {trace_id}, skipping RAGAS")
        return

    metrics = [
        ("faithfulness",      Faithfulness(llm=llm),                          {"retrieved_contexts": contexts}),
        ("answer_relevancy",  AnswerRelevancy(llm=llm, embeddings=emb),        {}),
        ("context_precision", ContextPrecisionWithoutReference(llm=llm),       {"retrieved_contexts": contexts}),
    ]

    for name, metric, extra in metrics:
        try:
            result = await metric.ascore(user_input=query, response=answer, **extra)
            value = float(result.value)
            score_trace(trace_id, name, value, comment="ragas")
            logger.debug(f"[layer2] {name}={value:.4f} trace={trace_id}")
        except Exception as e:
            logger.warning(f"[layer2] RAGAS {name} failed trace={trace_id}: {e}")


# ── LLM-as-judge ──────────────────────────────────────────────────────────────

_JUDGE_MODEL = "gpt-4o"  # stronger model than the generation model (gpt-4o-mini)


def _run_llm_judge(trace_id: str, query: str, answer: str) -> None:
    client = _make_sync_client()
    if client is None:
        return

    prompt = (
        "You are an impartial evaluator. Rate how well the user profile below answers the question.\n\n"
        f"Question: {query}\n\n"
        f"Profile:\n{answer}\n\n"
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
        raw = resp.choices[0].message.content.strip()
        value = max(0.0, min(1.0, float(raw)))
        score_trace(trace_id, "profile_relevance", value, comment="llm_judge")
        logger.debug(f"[layer2] profile_relevance={value:.4f} trace={trace_id}")
    except Exception as e:
        logger.warning(f"[layer2] LLM judge failed trace={trace_id}: {e}")


# ── background thread ─────────────────────────────────────────────────────────

def _background_eval(
    trace_id: str,
    query: str,
    answer: str,
    intent: str,
    doc_hits: List[Dict],
    artifact_hits: List[Dict],
    user_hits: List[Dict],
    exact_match: bool,
) -> None:
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

        lf = _get_langfuse()
        if lf:
            lf.flush()
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
    """
    Fire-and-forget Layer 2 quality evaluation in a daemon thread.

    exact_match=True  → LLM-as-judge (profile_relevance score)
    otherwise         → RAGAS faithfulness / answer_relevancy / context_precision
    """
    if not trace_id or not answer:
        return

    t = threading.Thread(
        target=_background_eval,
        args=(
            trace_id, query, answer, intent,
            doc_hits or [], artifact_hits or [], user_hits or [],
            exact_match,
        ),
        daemon=True,
        name=f"layer2-{trace_id[:8]}",
    )
    t.start()
    logger.debug(f"[layer2] eval dispatched trace={trace_id} intent={intent} exact={exact_match}")
