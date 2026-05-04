"""
Drop-in replacement for src/observability/llm_client.py in a Databricks environment.

Points the OpenAI client at Databricks serving-endpoints instead of a LiteLLM proxy.
The API is identical (OpenAI-compatible), so all callers in engine.py / classifier.py
/ query_rewriter.py etc. work without changes.

litellm_metadata() becomes a no-op: span grouping is handled by MLflow context
managers in engine.py, not by HTTP header forwarding.
"""

import os
from typing import Dict, List, Optional

from openai import OpenAI


def make_llm_client() -> OpenAI:
    """Return an OpenAI client pointed at Databricks Model Serving."""
    host  = os.environ["DATABRICKS_HOST"].rstrip("/")
    token = os.environ["DATABRICKS_TOKEN"]
    return OpenAI(
        api_key=token,
        base_url=f"{host}/serving-endpoints",
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
    # No-op: MLflow context managers handle span grouping; no proxy headers needed.
    return {}
