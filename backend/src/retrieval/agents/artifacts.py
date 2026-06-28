"""Artifact discovery specialist agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...observability import evaluate_in_background
from ..chatbot.prompts import build_artifact_search_messages
from .types import AgentContext, AgentResult


class ArtifactAgent:
    """Searches notebook/script summaries and explains relevant artifacts."""

    name = "artifact"

    def __init__(
        self,
        artifact_retriever: Any,
        llm_client: Optional[Any] = None,
        llm_model: str = "gpt-4o-mini",
    ):
        self.artifact_retriever = artifact_retriever
        self.llm_client = llm_client
        self.llm_model = llm_model

    def run(self, context: AgentContext, top_k: int = 5) -> Optional[Dict]:
        if context.intent != "ARTIFACT_SEARCH":
            context.add_step(self.name, "pass")
            return None

        query = context.search_query or context.query
        artifact_hits = self.artifact_retriever.retrieve(query, top_k=top_k)
        context.add_step(
            self.name,
            "search_artifacts",
            hit_count=len(artifact_hits),
            query=query,
        )
        answer = self._generate_answer(context, artifact_hits)
        result = AgentResult(
            answer=answer,
            intent="ARTIFACT_SEARCH",
            confidence=max(context.confidence, 0.75) if artifact_hits else 0.7,
            raw_artifacts=artifact_hits,
        ).to_response()
        evaluate_in_background(
            context.trace_id or "",
            context.query,
            answer,
            intent="ARTIFACT_SEARCH",
            artifact_hits=artifact_hits,
        )
        return result

    def _generate_answer(self, context: AgentContext, artifact_hits: List[Dict]) -> str:
        if not artifact_hits:
            return "I couldn't find matching notebooks, scripts, or artifacts for this query."

        if not self.llm_client:
            titles = ", ".join(hit.get("artifact_id", "unknown") for hit in artifact_hits[:3])
            return f"Relevant artifacts I found: {titles}."

        messages = build_artifact_search_messages(artifact_hits, context.query)
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.2,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            titles = ", ".join(hit.get("artifact_id", "unknown") for hit in artifact_hits[:3])
            return f"Relevant artifacts I found: {titles}."
