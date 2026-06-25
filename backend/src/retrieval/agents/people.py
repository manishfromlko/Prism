"""People/Profile specialist agent."""

from __future__ import annotations

from typing import Dict, Optional

from ...observability import evaluate_in_background
from ..chatbot.formatter import format_response
from ..chatbot.memory import resolve_user_from_context
from ..chatbot.user_resolver import UserNameResolver, retrieve_candidates
from ..user_profile_store import UserProfileStore
from .types import AgentContext


class PeopleProfileAgent:
    """Handles deterministic user-name resolution and profile lookup."""

    name = "people_profile"

    def __init__(self, user_store: UserProfileStore, user_resolver: UserNameResolver):
        self.user_store = user_store
        self.user_resolver = user_resolver

    def run(self, context: AgentContext) -> Optional[Dict]:
        all_ids = self.user_store.get_all_user_ids()
        context.add_step(self.name, "load_user_roster", user_count=len(all_ids))

        contextual_uid = resolve_user_from_context(context.query, context.history, all_ids)
        if contextual_uid:
            context.add_step(self.name, "resolve_from_conversation", user_id=contextual_uid)
            return self._profile_response(context, contextual_uid)

        name_candidates = retrieve_candidates(context.query, all_ids)
        if not name_candidates:
            context.add_step(self.name, "no_name_candidates")
            return None

        context.add_step(
            self.name,
            "resolve_name_candidates",
            candidate_count=len(name_candidates),
            top_candidate=name_candidates[0][0],
            top_score=round(name_candidates[0][1], 2),
        )
        resolved = self.user_resolver.resolve(
            context.query,
            candidates=name_candidates,
            trace_id=context.trace_id,
        )
        if resolved.get("exact_uid"):
            return self._profile_response(context, resolved["exact_uid"])

        context.add_step(self.name, "ask_user_to_disambiguate")
        return format_response(
            answer=resolved["answer"],
            intent="USER_SEARCH",
            confidence=0.5,
        )

    def _profile_response(self, context: AgentContext, user_id: str) -> Optional[Dict]:
        profile = self.user_store.get_profile(user_id)
        if not profile:
            context.add_step(self.name, "profile_missing", user_id=user_id)
            return None

        answer = f"**{user_id}**\n\n{profile['user_profile']}"
        result = format_response(
            answer=answer,
            intent="USER_SEARCH",
            confidence=1.0,
            raw_users=[profile],
            exact_match=True,
        )
        evaluate_in_background(
            context.trace_id or "",
            context.query,
            answer,
            intent="USER_SEARCH",
            exact_match=True,
        )
        context.add_step(self.name, "return_profile", user_id=user_id)
        return result
