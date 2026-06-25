"""Trace scoring utilities for the RAG pipeline.

LangSmith traces the chat pipeline and nested OpenAI calls. This module posts
feedback scores onto those LangSmith traces.

Scores posted per request:
  response_length    — normalised answer length (penalises very short/long)
  has_content        — 1.0 if answer looks substantive, 0.0 if it's a fallback
  intent_confidence  — classifier confidence passed through directly (0–1)
  source_count       — number of retrieved sources, normalised over 5 (0–1)

User-initiated feedback (via /observability/feedback):
  user_feedback      — thumbs up = 1.0, thumbs down = 0.0

RAGAS-based scoring (faithfulness, context relevance, answer relevance) is
Layer 2 and is not included here.

All functions are no-ops when LangSmith tracing is not configured.

Environment variables:
  LANGSMITH_TRACING  — true/false tracing switch
  LANGSMITH_API_KEY  — LangSmith API key
  LANGSMITH_ENDPOINT — LangSmith API endpoint
  LANGSMITH_PROJECT  — project name
"""

import logging
import os
from typing import Optional

from .mlflow_tracing import log_mlflow_score

logger = logging.getLogger(__name__)

_MIN_ANSWER_CHARS = 50
_MAX_ANSWER_CHARS = 2000
_SOURCE_NORM = 5  # 5 sources = score 1.0; scales linearly below that

try:
    from langsmith import Client
    _LANGSMITH_AVAILABLE = True
except ImportError:
    Client = None
    _LANGSMITH_AVAILABLE = False

_langsmith_instance = None


def _langsmith_enabled() -> bool:
    enabled = os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "false"))
    api_key = os.getenv("LANGSMITH_API_KEY", os.getenv("LANGCHAIN_API_KEY", ""))
    return enabled.lower() in {"1", "true", "yes", "on"} and bool(api_key)


def _get_langsmith():
    global _langsmith_instance
    if _langsmith_instance is not None:
        return _langsmith_instance
    if not _LANGSMITH_AVAILABLE or not _langsmith_enabled() or Client is None:
        return None
    _langsmith_instance = Client(
        api_url=os.getenv("LANGSMITH_ENDPOINT", os.getenv("LANGCHAIN_ENDPOINT")),
        api_key=os.getenv("LANGSMITH_API_KEY", os.getenv("LANGCHAIN_API_KEY")),
    )
    return _langsmith_instance


def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: Optional[str] = None,
) -> None:
    """Post a named numeric feedback score to configured tracing backends."""
    log_mlflow_score(trace_id, name, round(float(value), 4), comment)

    client = _get_langsmith()
    if not client or not trace_id:
        return
    try:
        client.create_feedback(
            trace_id=trace_id,
            key=name,
            score=round(float(value), 4),
            value=round(float(value), 4),
            comment=comment,
        )
        logger.debug(f"Score queued: trace={trace_id} name={name} value={value:.4f}")
    except Exception as e:
        logger.warning(f"Failed to post score '{name}' to trace {trace_id}: {e}")


def score_user_feedback(trace_id: str, thumbs_up: bool) -> None:
    """
    Record binary user feedback (thumbs up = 1.0, thumbs down = 0.0).
    Appears in LangSmith as feedback key 'user_feedback'.
    """
    score_trace(
        trace_id=trace_id,
        name="user_feedback",
        value=1.0 if thumbs_up else 0.0,
        comment="thumbs_up" if thumbs_up else "thumbs_down",
    )


def score_response_quality(
    trace_id: str,
    answer: str,
    intent: str,
    confidence: float = 0.0,
    source_count: int = 0,
) -> None:
    """
    Post heuristic quality scores for one request. No LLM call — runs inline.

    Scores:
      response_length   — normalised answer length; peaks at 300–2000 chars
      has_content       — 1.0 if answer is substantive, 0.0 if fallback phrase
      intent_confidence — classifier confidence forwarded as-is (already 0–1)
      source_count      — retrieved sources / _SOURCE_NORM, capped at 1.0

    Args:
        trace_id:    LangSmith trace ID to attach scores to.
        answer:      Final answer text returned to the user.
        intent:      Resolved intent string (DOC_QA, ARTIFACT_SEARCH, etc.).
        confidence:  Classifier confidence in [0, 1].
        source_count: Total retrieved sources (docs + artifacts + users).
    """
    if not trace_id or not answer:
        return

    # ── response_length ──────────────────────────────────────────────────────
    n = len(answer.strip())
    if n < _MIN_ANSWER_CHARS:
        length_score = n / _MIN_ANSWER_CHARS * 0.5
    elif n <= 300:
        length_score = 0.5 + (n - _MIN_ANSWER_CHARS) / (300 - _MIN_ANSWER_CHARS) * 0.5
    elif n <= _MAX_ANSWER_CHARS:
        length_score = 1.0
    else:
        length_score = max(0.5, 1.0 - (n - _MAX_ANSWER_CHARS) / _MAX_ANSWER_CHARS * 0.3)

    # ── has_content ──────────────────────────────────────────────────────────
    _FALLBACK_PHRASES = [
        "i couldn't find",
        "i don't have access",
        "i encountered an error",
        "please try again",
        "outside what i can help",
        "no matching",
    ]
    has_content = 0.0 if any(p in answer.lower() for p in _FALLBACK_PHRASES) else 1.0

    # ── source_count ─────────────────────────────────────────────────────────
    src_score = min(1.0, source_count / _SOURCE_NORM) if source_count > 0 else 0.0

    # ── post all scores then flush so they appear immediately ────────────────
    score_trace(trace_id, "response_length",   length_score,            f"chars={n}")
    score_trace(trace_id, "has_content",        has_content,             f"intent={intent}")
    score_trace(trace_id, "intent_confidence",  min(1.0, float(confidence)), f"intent={intent}")
    score_trace(trace_id, "source_count",       src_score,               f"sources={source_count}")
