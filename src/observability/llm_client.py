"""
Factory for an OpenAI-compatible client routed through the LiteLLM proxy.

All LLM calls in this project use make_llm_client() so that:
  - Every call routes through the LiteLLM proxy (localhost:4000)
  - The proxy's Langfuse callback captures token usage, cost, and latency
    automatically — no per-call instrumentation needed in application code
  - Model aliases (gpt-4o-mini, text-embedding-3-small) are resolved centrally
    in the proxy config, not scattered across the codebase

Grouping multiple LLM calls under a single Langfuse trace:
  Pass extra_body=litellm_metadata(trace_id, "classify") to each completion
  call. LiteLLM forwards this metadata to Langfuse so all generations in one
  user request appear under the same trace.

  On the final (generate) call, also pass trace_name, tags, and trace_metadata
  to enrich the root trace in Langfuse with query context and intent details.

Environment variables (set in .env):
  LITELLM_BASE_URL  — proxy address, default http://localhost:4000
  LITELLM_API_KEY   — proxy API key, default sk-1234
"""

import os
from typing import Dict, List, Optional

from openai import OpenAI


def make_llm_client() -> OpenAI:
    """Return an OpenAI client pointed at the LiteLLM proxy."""
    return OpenAI(
        api_key=os.getenv("LITELLM_API_KEY", "sk-1234"),
        base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    )


def litellm_metadata(
    trace_id: str,
    generation_name: str,
    session_id: Optional[str] = None,
    trace_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    trace_metadata: Optional[Dict] = None,
    trace_user_id: Optional[str] = None,
) -> dict:
    """
    Build the extra_body dict to pass trace context to the LiteLLM proxy.
    The proxy forwards this to Langfuse so all generations in one request
    appear under the same trace with full context.

    Args:
        trace_id:       UUID that groups all generations in one request.
        generation_name: Short label for this generation span (e.g. "classify").
        session_id:     Conversation session ID — groups traces into a session.
        trace_name:     Human-readable root trace name in Langfuse.
                        Set this on the final generate call so it reflects the
                        resolved intent (e.g. "chat · DOC_QA").
        tags:           List of string tags on the root trace
                        (e.g. ["intent:DOC_QA", "model:gpt-4o-mini"]).
        trace_metadata: Dict of extra metadata stored on the root trace
                        (e.g. {"query": "...", "intent": "DOC_QA", "confidence": 0.9}).
        trace_user_id:  User identifier shown in Langfuse user analytics.

    Usage:
        # Early pipeline steps — minimal context
        extra_body=litellm_metadata(trace_id, "classify")

        # Final generate step — full context enriches the root trace
        extra_body=litellm_metadata(
            trace_id, "generate",
            session_id=session_id,
            trace_name=f"chat · {intent}",
            tags=[f"intent:{intent}", f"model:{model}"],
            trace_metadata={"query": query, "intent": intent, "confidence": confidence},
        )
    """
    metadata: dict = {"trace_id": trace_id, "generation_name": generation_name}
    if session_id:
        metadata["session_id"] = session_id
    if trace_name:
        metadata["trace_name"] = trace_name
    if tags:
        metadata["tags"] = tags
    if trace_metadata:
        metadata["trace_metadata"] = trace_metadata
    if trace_user_id:
        metadata["trace_user_id"] = trace_user_id
    return {"metadata": metadata}
