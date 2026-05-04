"""Intent classifier: maps user query → DOC_QA | ARTIFACT_SEARCH | USER_SEARCH | HYBRID | OUT_OF_SCOPE."""

import json
import logging
from typing import Dict, Optional

from ...observability import litellm_metadata
from ..config import make_openai_client
from .prompt_loader import load_prompt

logger = logging.getLogger(__name__)

INTENTS = {"DOC_QA", "ARTIFACT_SEARCH", "USER_SEARCH", "HYBRID", "OUT_OF_SCOPE"}


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
        trace_id is forwarded to LiteLLM so this generation is grouped under
        the same Langfuse trace as the rest of the request pipeline.
        """
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
                extra_body=litellm_metadata(trace_id, "classify") if trace_id else None,
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
