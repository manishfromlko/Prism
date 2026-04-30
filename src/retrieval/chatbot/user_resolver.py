"""LLM-based name resolver for user/workspace disambiguation."""

import logging
import os
from typing import Dict, List

from openai import OpenAI

from ..user_profile_store import UserProfileStore
from .prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class UserNameResolver:
    """
    Resolves a partial name query (e.g. "ravi", "verma") to a short,
    ranked list of actual user_ids by asking an LLM to apply string-
    matching rules against the full roster — not vector similarity.
    """

    def __init__(self, user_store: UserProfileStore, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.user_store = user_store
        self._system_prompt = load_prompt("chatbot/user_resolution/system.txt")
        self._user_template = load_prompt("chatbot/user_resolution/user.txt")

    def resolve(self, query: str) -> Dict:
        """
        Returns:
            {
                "answer": str,       # formatted Top Matches + optional Follow-up
                "matched_ids": list  # user_ids extracted from the LLM response
            }
        """
        all_ids = self.user_store.get_all_user_ids()
        if not all_ids:
            return {
                "answer": "No user profiles are indexed yet. Please run the profile indexer first.",
                "matched_ids": [],
            }

        available_names = "\n".join(f"- {uid}" for uid in sorted(all_ids))
        user_message = self._user_template.format(
            user_query=query,
            available_names=available_names,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,
                max_tokens=300,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"UserNameResolver LLM call failed: {e}")
            answer = "I had trouble resolving that name. Please try using the full username."

        # Extract matched user_ids that appear verbatim in the LLM response
        matched_ids = [uid for uid in all_ids if uid in answer]

        return {"answer": answer, "matched_ids": matched_ids}
