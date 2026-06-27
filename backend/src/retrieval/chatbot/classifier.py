"""Intent classifier for enterprise RAG and chat-control flows."""

import json
import logging
from typing import Dict, Optional

from ...observability import trace_extra_body
from ..config import make_openai_client
from .memory import (
    is_conversation_memory_query,
    is_greeting,
    is_self_intro_query,
    is_system_stats_query,
)
from .prompt_loader import load_prompt

logger = logging.getLogger(__name__)

INTENTS = {
    "DOC_QA",
    "ARTIFACT_SEARCH",
    "USER_SEARCH",
    "HYBRID",
    "GREETING",
    "SELF_INTRO",
    "SYSTEM_STATS",
    "CONVERSATION_MEMORY",
    "OUT_OF_SCOPE",
}


class IntentClassifier:
    """Uses an LLM to classify query intent."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = make_openai_client()
        self.model = model
        self._system_prompt = load_prompt("chatbot/classifier/system.txt")

    def classify(self, query: str, trace_id: Optional[str] = None) -> Dict:
        """
        Returns dict: {intent, confidence, reasoning}
        Falls back to DOC_QA with low confidence on failure.
        trace_id is associated with the request-level LangSmith trace.
        """
        if is_greeting(query):
            return {
                "intent": "GREETING",
                "confidence": 0.99,
                "reasoning": "Simple conversational greeting.",
            }

        if is_self_intro_query(query):
            return {
                "intent": "SELF_INTRO",
                "confidence": 0.99,
                "reasoning": "User is asking about assistant capabilities.",
            }

        if is_system_stats_query(query):
            return {
                "intent": "SYSTEM_STATS",
                "confidence": 0.99,
                "reasoning": "User is asking for indexed workspace metadata counts.",
            }

        if is_conversation_memory_query(query):
            return {
                "intent": "CONVERSATION_MEMORY",
                "confidence": 0.99,
                "reasoning": "User is asking about the current conversation history.",
            }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": f"Query: {query}"},
                ],
                temperature=0.0,
                max_tokens=150,
                response_format={"type": "json_object"},
                extra_body=trace_extra_body(trace_id, "classify") if trace_id else None,
            )
            raw = response.choices[0].message.content
            result = json.loads(raw)

            intent = result.get("intent", "DOC_QA").upper()
            if intent not in INTENTS:
                intent = "DOC_QA"

            return {
                "intent": intent,
                "confidence": float(result.get("confidence", 0.5)),
                "reasoning": result.get("reasoning", ""),
            }
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return {"intent": "DOC_QA", "confidence": 0.3, "reasoning": f"Classification error: {e}"}
