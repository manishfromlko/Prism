"""Answer synthesis specialist agent."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .types import AgentContext

PromptBuilder = Callable[[List[Dict], str], List[Dict]]
FallbackBuilder = Callable[[List[Dict]], str]


class SynthesisAgent:
    """Composes final natural-language answers from retrieved evidence."""

    name = "synthesis"

    def __init__(self, llm_client: Optional[Any] = None, llm_model: str = "gpt-4o-mini"):
        self.llm_client = llm_client
        self.llm_model = llm_model

    def synthesize(
        self,
        context: AgentContext,
        *,
        evidence: List[Dict],
        prompt_builder: PromptBuilder,
        fallback_builder: FallbackBuilder,
        empty_answer: str,
        max_tokens: int = 600,
    ) -> str:
        if not evidence:
            context.add_step(self.name, "empty_answer")
            return empty_answer

        if not self.llm_client:
            context.add_step(self.name, "fallback_answer", reason="llm_client_unavailable")
            return fallback_builder(evidence)

        messages = prompt_builder(evidence, context.query)
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.2,
                max_tokens=max_tokens,
            )
            context.add_step(self.name, "generate_answer", model=self.llm_model)
            return response.choices[0].message.content.strip()
        except Exception as exc:
            context.add_step(
                self.name,
                "fallback_answer",
                reason="llm_generation_failed",
                error=str(exc),
            )
            return fallback_builder(evidence)
