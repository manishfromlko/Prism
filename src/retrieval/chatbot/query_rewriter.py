"""Query rewriting layer — optimise user query for semantic search."""

import logging
from typing import Optional

from ...observability import litellm_metadata
from ..config import make_openai_client
from .prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class QueryRewriter:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = make_openai_client()
        self.model = model
        self._system_prompt = load_prompt("chatbot/query_rewriter/system.txt")

    def rewrite(self, query: str, trace_id: Optional[str] = None) -> str:
        """Return a semantically enriched query string."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0.0,
                max_tokens=80,
                extra_body=litellm_metadata(trace_id, "rewrite") if trace_id else None,
            )
            rewritten = response.choices[0].message.content.strip()
            logger.debug(f"Query rewritten: '{query}' → '{rewritten}'")
            return rewritten or query
        except Exception as e:
            logger.warning(f"Query rewriting failed, using original: {e}")
            return query
