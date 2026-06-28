"""Platform documentation specialist agent."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...observability import evaluate_in_background
from ..chatbot.prompts import build_doc_qa_messages
from .synthesis import SynthesisAgent
from .types import AgentContext, AgentResult


class DocsAgent:
    """Answers platform how-to and documentation questions."""

    name = "docs"

    def __init__(
        self,
        doc_retriever: Any,
        synthesis_agent: Optional[SynthesisAgent] = None,
    ):
        self.doc_retriever = doc_retriever
        self.synthesis_agent = synthesis_agent or SynthesisAgent()

    def run(self, context: AgentContext, top_k: int = 5) -> Optional[Dict]:
        if context.intent != "DOC_QA":
            context.add_step(self.name, "pass")
            return None

        query = context.search_query or context.query
        doc_hits = self.doc_retriever.retrieve(query, top_k=top_k)
        context.add_step(self.name, "search_platform_docs", hit_count=len(doc_hits), query=query)
        answer = self.synthesis_agent.synthesize(
            context,
            evidence=doc_hits,
            prompt_builder=build_doc_qa_messages,
            fallback_builder=self._fallback_answer,
            empty_answer="I couldn't find relevant platform documentation for this question.",
        )
        result = AgentResult(
            answer=answer,
            intent="DOC_QA",
            confidence=max(context.confidence, 0.75) if doc_hits else 0.65,
            raw_docs=doc_hits,
        ).to_response()
        evaluate_in_background(
            context.trace_id or "",
            context.query,
            answer,
            intent="DOC_QA",
            doc_hits=doc_hits,
        )
        return result

    @staticmethod
    def _fallback_answer(doc_hits: list[Dict]) -> str:
        sources = ", ".join(hit.get("source_file", "unknown") for hit in doc_hits[:3])
        return f"Relevant platform documentation I found: {sources}."
