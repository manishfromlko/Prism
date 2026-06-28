"""Platform documentation specialist agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...observability import evaluate_in_background
from ..chatbot.prompts import build_doc_qa_messages
from .types import AgentContext, AgentResult


class DocsAgent:
    """Answers platform how-to and documentation questions."""

    name = "docs"

    def __init__(
        self,
        doc_retriever: Any,
        llm_client: Optional[Any] = None,
        llm_model: str = "gpt-4o-mini",
    ):
        self.doc_retriever = doc_retriever
        self.llm_client = llm_client
        self.llm_model = llm_model

    def run(self, context: AgentContext, top_k: int = 5) -> Optional[Dict]:
        if context.intent != "DOC_QA":
            context.add_step(self.name, "pass")
            return None

        query = context.search_query or context.query
        doc_hits = self.doc_retriever.retrieve(query, top_k=top_k)
        context.add_step(self.name, "search_platform_docs", hit_count=len(doc_hits), query=query)
        answer = self._generate_answer(context, doc_hits)
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

    def _generate_answer(self, context: AgentContext, doc_hits: List[Dict]) -> str:
        if not doc_hits:
            return "I couldn't find relevant platform documentation for this question."

        if not self.llm_client:
            sources = ", ".join(hit.get("source_file", "unknown") for hit in doc_hits[:3])
            return f"Relevant platform documentation I found: {sources}."

        messages = build_doc_qa_messages(doc_hits, context.query)
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.2,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            sources = ", ".join(hit.get("source_file", "unknown") for hit in doc_hits[:3])
            return f"Relevant platform documentation I found: {sources}."
