"""OpenAI client factory and LangSmith tracing helpers."""

import os
from typing import Dict, List, Optional

from openai import OpenAI

try:
    from langsmith.wrappers import wrap_openai
    _LANGSMITH_WRAPPER_AVAILABLE = True
except ImportError:
    wrap_openai = None
    _LANGSMITH_WRAPPER_AVAILABLE = False


def is_langsmith_enabled() -> bool:
    """Return True when LangSmith tracing is configured for this process."""
    enabled = os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "false"))
    api_key = os.getenv("LANGSMITH_API_KEY", os.getenv("LANGCHAIN_API_KEY", ""))
    return enabled.lower() in {"1", "true", "yes", "on"} and bool(api_key)


def make_llm_client() -> OpenAI:
    """Return a direct OpenAI client, wrapped for LangSmith tracing if enabled."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for direct OpenAI calls")

    client = OpenAI(api_key=api_key)
    if is_langsmith_enabled() and _LANGSMITH_WRAPPER_AVAILABLE and wrap_openai:
        return wrap_openai(client)
    return client


def trace_extra_body(
    trace_id: str,
    generation_name: str,
    session_id: Optional[str] = None,
    trace_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    trace_metadata: Optional[Dict] = None,
    trace_user_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Compatibility hook for OpenAI calls.

    Direct OpenAI calls do not need an ``extra_body`` for observability.
    LangSmith tracing is handled by wrapping the OpenAI client and by tracing
    the top-level chat pipeline. The parameters stay here so call sites can pass
    rich context without knowing which observability backend is active.

    Args:
        trace_id:       Application trace UUID returned to the frontend.
        generation_name: Short label for this generation span, e.g. "classify".
        session_id:     Conversation session ID.
        trace_name:     Human-readable root trace name.
        tags:           List of tags
                        (e.g. ["intent:DOC_QA", "model:gpt-4o-mini"]).
        trace_metadata: Dict of extra metadata
                        (e.g. {"query": "...", "intent": "DOC_QA", "confidence": 0.9}).
        trace_user_id:  User identifier.
    """
    return None
