"""
Trace scoring utilities for the RAG pipeline.

The LiteLLM proxy automatically logs all LLM API calls to Langfuse (tokens,
cost, latency, prompt/response).  This module's sole job is posting *scores*
onto those traces — something the proxy doesn't do on its own.

Scores posted per request:
  response_length    — normalised answer length (penalises very short/long)
  has_content        — 1.0 if answer looks substantive, 0.0 if it's a fallback
  intent_confidence  — classifier confidence passed through directly (0–1)
  source_count       — number of retrieved sources, normalised over 5 (0–1)

User-initiated scores (via /observability/feedback):
  user_feedback      — thumbs up = 1.0, thumbs down = 0.0

RAGAS-based scoring (faithfulness, context relevance, answer relevance) is
Layer 2 and is not included here.

All functions are no-ops when LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are
unset or contain placeholder values.

Environment variables:
  LANGFUSE_PUBLIC_KEY  — Langfuse project public key
  LANGFUSE_SECRET_KEY  — Langfuse project secret key
  LANGFUSE_HOST        — Langfuse server URL (default http://localhost:3001)
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_MIN_ANSWER_CHARS = 50
_MAX_ANSWER_CHARS = 2000
_SOURCE_NORM = 5  # 5 sources = score 1.0; scales linearly below that

try:
    from langfuse import Langfuse
    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False

_langfuse_instance = None


def _get_langfuse():
    global _langfuse_instance
    if _langfuse_instance is not None:
        return _langfuse_instance
    if not _LANGFUSE_AVAILABLE:
        return None
    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk = os.getenv("LANGFUSE_SECRET_KEY", "")
    if not pk or pk.startswith("your-"):
        return None
    _langfuse_instance = Langfuse(
        public_key=pk,
        secret_key=sk,
        host=os.getenv("LANGFUSE_HOST", "http://localhost:3001"),
    )
    return _langfuse_instance


def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: Optional[str] = None,
) -> None:
    """Post a named numeric score to a Langfuse trace. value must be in [0, 1]."""
    lf = _get_langfuse()
    if not lf or not trace_id:
        return
    try:
        lf.create_score(
            trace_id=trace_id,
            name=name,
            value=round(float(value), 4),
            comment=comment,
        )
        logger.debug(f"Score queued: trace={trace_id} name={name} value={value:.4f}")
    except Exception as e:
        logger.warning(f"Failed to post score '{name}' to trace {trace_id}: {e}")


def score_user_feedback(trace_id: str, thumbs_up: bool) -> None:
    """
    Record binary user feedback (thumbs up = 1.0, thumbs down = 0.0).
    Appears in Langfuse as score name 'user_feedback'.
    """
    score_trace(
        trace_id=trace_id,
        name="user_feedback",
        value=1.0 if thumbs_up else 0.0,
        comment="thumbs_up" if thumbs_up else "thumbs_down",
    )
    lf = _get_langfuse()
    if lf:
        lf.flush()


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
        trace_id:    Langfuse trace ID to attach scores to.
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
    lf = _get_langfuse()
    if lf:
        lf.flush()
