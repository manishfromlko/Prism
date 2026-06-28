"""Hybrid retrieval coordinator agent."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...observability import evaluate_in_background
from ..chatbot.prompts import build_hybrid_messages
from .synthesis import SynthesisAgent
from .types import AgentContext, AgentResult


class HybridAgent:
    """Coordinates docs, artifacts, and people retrieval for mixed questions."""

    name = "hybrid"

    def __init__(
        self,
        doc_retriever: Any,
        artifact_retriever: Any,
        user_retriever: Any,
        synthesis_agent: Optional[SynthesisAgent] = None,
    ):
        self.doc_retriever = doc_retriever
        self.artifact_retriever = artifact_retriever
        self.user_retriever = user_retriever
        self.synthesis_agent = synthesis_agent or SynthesisAgent()

    def run(self, context: AgentContext, top_k: int = 3) -> Optional[Dict]:
        if context.intent != "HYBRID":
            context.add_step(self.name, "pass")
            return None

        query = context.search_query or context.query
        doc_hits = self.doc_retriever.retrieve(query, top_k=top_k)
        artifact_hits = self.artifact_retriever.retrieve(query, top_k=top_k)
        user_hits = self.user_retriever.retrieve(query, top_k=top_k)
        context.add_step(
            self.name,
            "search_all_sources",
            doc_hits=len(doc_hits),
            artifact_hits=len(artifact_hits),
            user_hits=len(user_hits),
            query=query,
        )

        evidence = {
            "docs": doc_hits,
            "artifacts": artifact_hits,
            "users": user_hits,
        }
        answer = self.synthesis_agent.synthesize(
            context,
            evidence=[evidence] if any(evidence.values()) else [],
            prompt_builder=lambda _items, original_query: build_hybrid_messages(
                doc_hits,
                artifact_hits,
                user_hits,
                original_query,
            ),
            fallback_builder=lambda _items: self._fallback_answer(
                doc_hits,
                artifact_hits,
                user_hits,
            ),
            empty_answer="I couldn't find relevant docs, artifacts, or people for this query.",
        )
        result = AgentResult(
            answer=answer,
            intent="HYBRID",
            confidence=max(context.confidence, 0.75) if any(evidence.values()) else 0.65,
            raw_docs=doc_hits,
            raw_artifacts=artifact_hits,
            raw_users=user_hits,
        ).to_response()
        evaluate_in_background(
            context.trace_id or "",
            context.query,
            answer,
            intent="HYBRID",
            doc_hits=doc_hits,
            artifact_hits=artifact_hits,
            user_hits=user_hits,
        )
        return result

    @staticmethod
    def _fallback_answer(doc_hits: list[Dict], artifact_hits: list[Dict], user_hits: list[Dict]) -> str:
        parts = []
        if doc_hits:
            parts.append(f"docs: {', '.join(hit.get('source_file', 'unknown') for hit in doc_hits[:2])}")
        if artifact_hits:
            parts.append(f"artifacts: {', '.join(hit.get('artifact_id', 'unknown') for hit in artifact_hits[:2])}")
        if user_hits:
            parts.append(f"people: {', '.join(hit.get('user_id', 'unknown') for hit in user_hits[:2])}")
        return "Relevant matches I found across the workspace: " + "; ".join(parts) + "."
