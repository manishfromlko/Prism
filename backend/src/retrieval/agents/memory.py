"""Conversation-memory and assistant-control specialist agent."""

from __future__ import annotations

from typing import Optional

from ..chatbot.memory import (
    answer_conversation_memory_query,
    greeting_answer,
    is_conversation_memory_query,
    is_greeting,
    is_self_intro_query,
    self_intro_answer,
)
from .types import AgentContext, AgentResult


class MemoryAgent:
    """Handles conversation-local questions without retrieval."""

    name = "memory"

    def run(self, context: AgentContext) -> Optional[AgentResult]:
        intent = context.intent
        query = context.query

        if intent == "SELF_INTRO" or is_self_intro_query(query):
            context.add_step(self.name, "answer_self_intro")
            return AgentResult(
                answer=self_intro_answer(),
                intent="SELF_INTRO",
                confidence=max(context.confidence, 0.95),
            )

        if intent == "GREETING" or is_greeting(query):
            context.add_step(self.name, "answer_greeting")
            return AgentResult(
                answer=greeting_answer(),
                intent="GREETING",
                confidence=max(context.confidence, 0.95),
            )

        if intent == "CONVERSATION_MEMORY" or is_conversation_memory_query(query):
            context.add_step(self.name, "answer_conversation_memory")
            return AgentResult(
                answer=answer_conversation_memory_query(query, context.history),
                intent="CONVERSATION_MEMORY",
                confidence=max(context.confidence, 0.95),
            )

        context.add_step(self.name, "pass")
        return None
