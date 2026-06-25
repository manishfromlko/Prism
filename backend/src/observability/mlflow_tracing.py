"""MLflow tracing and metrics helpers for local observability."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager, nullcontext
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    _MLFLOW_AVAILABLE = False

_CONFIGURED = False


def is_mlflow_enabled() -> bool:
    enabled = os.getenv("MLFLOW_TRACING", "false")
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "")
    return _MLFLOW_AVAILABLE and enabled.lower() in {"1", "true", "yes", "on"} and bool(tracking_uri)


def _configure_mlflow() -> bool:
    global _CONFIGURED
    if not is_mlflow_enabled() or mlflow is None:
        return False
    if _CONFIGURED:
        return True
    try:
        os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "2")
        os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
        mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", "rag-chatbot"))
        _CONFIGURED = True
        return True
    except Exception as exc:
        logger.warning("MLflow tracing disabled after configuration failure: %s", exc)
        return False


def _safe_log_param(key: str, value: object) -> None:
    if mlflow is None:
        return
    try:
        mlflow.log_param(key, value)
    except Exception as exc:
        logger.debug("Failed to log MLflow param %s: %s", key, exc)


def _safe_set_tag(key: str, value: object) -> None:
    if mlflow is None:
        return
    try:
        mlflow.set_tag(key, value)
    except Exception as exc:
        logger.debug("Failed to set MLflow tag %s: %s", key, exc)


def _safe_log_metric(key: str, value: float) -> None:
    if mlflow is None:
        return
    try:
        mlflow.log_metric(key, float(value))
    except Exception as exc:
        logger.debug("Failed to log MLflow metric %s: %s", key, exc)


@contextmanager
def mlflow_chat_trace(
    query: str,
    history: Optional[List[Dict]] = None,
    session_id: Optional[str] = None,
) -> Iterator[object]:
    """Create a local MLflow run/span for one chat turn when enabled."""
    if not _configure_mlflow() or mlflow is None:
        yield None
        return

    history = history or []
    try:
        with mlflow.start_run(
            run_name="chat_pipeline",
            nested=mlflow.active_run() is not None,
        ) as run:
            _safe_set_tag("trace_backend", "mlflow")
            _safe_set_tag("session_id", session_id or "")
            _safe_set_tag("run_id", run.info.run_id)
            _safe_log_param("query", query[:500])
            _safe_log_param("history_turns", len(history))

            span_cm = (
                mlflow.start_span(
                    name="chat_pipeline",
                    span_type="CHAIN",
                    attributes={
                        "session_id": session_id or "",
                        "history_turns": len(history),
                    },
                    run_id=run.info.run_id,
                )
                if hasattr(mlflow, "start_span")
                else nullcontext(None)
            )
            with span_cm as span:
                if span is not None and hasattr(span, "set_inputs"):
                    span.set_inputs(
                        {
                            "query": query,
                            "session_id": session_id,
                            "history_turns": len(history),
                        }
                    )
                yield span
    except Exception as exc:
        logger.warning("MLflow chat tracing failed; continuing without MLflow trace: %s", exc)
        yield None


def record_mlflow_chat_output(span: object, result: Dict) -> None:
    """Attach chat result metadata to the current MLflow run/span."""
    if mlflow is None or not is_mlflow_enabled():
        return
    try:
        trace_id = result.get("trace_id", "")
        intent = result.get("intent", "")
        confidence = float(result.get("confidence", 0.0) or 0.0)
        source_count = len(result.get("sources", []))
        artifact_count = len(result.get("artifacts", []))
        user_count = len(result.get("users", []))

        _safe_set_tag("trace_id", trace_id)
        _safe_set_tag("intent", intent)
        _safe_set_tag("exact_match", result.get("exact_match", False))
        _safe_log_metric("intent_confidence", confidence)
        _safe_log_metric("source_count", source_count)
        _safe_log_metric("artifact_count", artifact_count)
        _safe_log_metric("user_count", user_count)

        if span is not None:
            if hasattr(span, "set_attributes"):
                span.set_attributes(
                    {
                        "trace_id": trace_id,
                        "intent": intent,
                        "confidence": confidence,
                        "exact_match": bool(result.get("exact_match", False)),
                    }
                )
            if hasattr(span, "set_outputs"):
                span.set_outputs(
                    {
                        "trace_id": trace_id,
                        "intent": intent,
                        "confidence": confidence,
                        "answer_preview": (result.get("answer") or "")[:500],
                    }
                )
    except Exception as exc:
        logger.debug("Failed to record MLflow chat output: %s", exc)


def log_mlflow_score(trace_id: str, name: str, value: float, comment: Optional[str] = None) -> None:
    """Log a score as an MLflow metric, using the active run when present."""
    if not _configure_mlflow() or mlflow is None or not trace_id:
        return
    try:
        active_run = mlflow.active_run()
        if active_run:
            _safe_set_tag("trace_id", trace_id)
            _safe_log_metric(name, value)
            if comment:
                _safe_set_tag(f"{name}_comment", comment[:250])
            return

        with mlflow.start_run(run_name=f"score_{name}"):
            _safe_set_tag("trace_id", trace_id)
            _safe_set_tag("score_name", name)
            if comment:
                _safe_set_tag("comment", comment[:250])
            _safe_log_metric(name, value)
    except Exception as exc:
        logger.debug("Failed to log MLflow score %s for trace %s: %s", name, trace_id, exc)
