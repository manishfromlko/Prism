"""
Drop-in replacement for src/observability/scoring.py in a Databricks environment.

Scores are posted to the active MLflow trace as metrics instead of Langfuse scores.
All function signatures are identical to the original so no call-site changes are needed.
"""

import logging
from typing import Optional

import mlflow

logger = logging.getLogger(__name__)

_MIN_ANSWER_CHARS = 50
_MAX_ANSWER_CHARS = 2000
_SOURCE_NORM = 5


def score_trace(trace_id: str, name: str, value: float, comment: Optional[str] = None) -> None:
    """Log a named score as an MLflow metric on the active run/trace."""
    try:
        mlflow.log_metric(name, round(float(value), 4))
        logger.debug(f"Score logged: trace={trace_id} name={name} value={value:.4f}")
    except Exception as e:
        logger.warning(f"Failed to log score '{name}': {e}")


def score_user_feedback(trace_id: str, thumbs_up: bool) -> None:
    """Record binary user feedback (thumbs up = 1.0, thumbs down = 0.0)."""
    score_trace(trace_id, "user_feedback", 1.0 if thumbs_up else 0.0,
                comment="thumbs_up" if thumbs_up else "thumbs_down")


def score_response_quality(
    trace_id: str,
    answer: str,
    intent: str,
    confidence: float = 0.0,
    source_count: int = 0,
) -> None:
    """Post heuristic Layer 1 quality scores. No LLM call — runs inline."""
    if not trace_id or not answer:
        return

    n = len(answer.strip())
    if n < _MIN_ANSWER_CHARS:
        length_score = n / _MIN_ANSWER_CHARS * 0.5
    elif n <= 300:
        length_score = 0.5 + (n - _MIN_ANSWER_CHARS) / (300 - _MIN_ANSWER_CHARS) * 0.5
    elif n <= _MAX_ANSWER_CHARS:
        length_score = 1.0
    else:
        length_score = max(0.5, 1.0 - (n - _MAX_ANSWER_CHARS) / _MAX_ANSWER_CHARS * 0.3)

    _FALLBACK_PHRASES = [
        "i couldn't find", "i don't have access", "i encountered an error",
        "please try again", "outside what i can help", "no matching",
    ]
    has_content = 0.0 if any(p in answer.lower() for p in _FALLBACK_PHRASES) else 1.0
    src_score   = min(1.0, source_count / _SOURCE_NORM) if source_count > 0 else 0.0

    mlflow.log_metrics({
        "response_length":   round(length_score, 4),
        "has_content":       has_content,
        "intent_confidence": round(min(1.0, float(confidence)), 4),
        "source_count":      round(src_score, 4),
    })
