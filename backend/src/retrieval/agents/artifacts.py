"""Artifact discovery specialist agent."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...observability import evaluate_in_background
from ..chatbot.prompts import build_artifact_search_messages
from .synthesis import SynthesisAgent
from .types import AgentContext, AgentResult


class ArtifactAgent:
    """Searches notebook/script summaries and explains relevant artifacts."""

    name = "artifact"

    def __init__(
        self,
        artifact_retriever: Any,
        synthesis_agent: Optional[SynthesisAgent] = None,
    ):
        self.artifact_retriever = artifact_retriever
        self.synthesis_agent = synthesis_agent or SynthesisAgent()

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
        answer = self.synthesis_agent.synthesize(
            context,
            evidence=artifact_hits,
            prompt_builder=build_artifact_search_messages,
            fallback_builder=self._fallback_answer,
            empty_answer="I couldn't find matching notebooks, scripts, or artifacts for this query.",
        )
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

    @staticmethod
    def _fallback_answer(artifact_hits: list[Dict]) -> str:
        titles = ", ".join(hit.get("artifact_id", "unknown") for hit in artifact_hits[:3])
        return f"Relevant artifacts I found: {titles}."
