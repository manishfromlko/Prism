"""People/Profile specialist agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...observability import evaluate_in_background
from ..chatbot.memory import resolve_user_from_context
from ..chatbot.prompts import build_user_search_messages
from ..chatbot.user_resolver import UserNameResolver, retrieve_candidates
from ..user_profile_store import UserProfileStore
from .types import AgentContext, AgentResult


class PeopleProfileAgent:
    """Handles deterministic user-name resolution and profile lookup."""

    name = "people_profile"

    def __init__(
        self,
        user_store: UserProfileStore,
        user_resolver: UserNameResolver,
        user_retriever: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        llm_model: str = "gpt-4o-mini",
    ):
        self.user_store = user_store
        self.user_resolver = user_resolver
        self.user_retriever = user_retriever
        self.llm_client = llm_client
        self.llm_model = llm_model

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
        return AgentResult(
            answer=resolved["answer"],
            intent="USER_SEARCH",
            confidence=0.5,
        ).to_response()

    def semantic_search(self, context: AgentContext, top_k: int = 5) -> Optional[Dict]:
        if not self.user_retriever:
            context.add_step(self.name, "semantic_search_unavailable")
            return None

        query = context.search_query or context.query
        user_hits = self.user_retriever.retrieve(query, top_k=top_k)
        context.add_step(
            self.name,
            "semantic_people_search",
            hit_count=len(user_hits),
            query=query,
        )
        if not user_hits:
            return AgentResult(
                answer="I couldn't find any matching users for this query in the knowledge base.",
                intent="USER_SEARCH",
                confidence=0.9,
                raw_users=[],
            ).to_response()

        answer = self._generate_people_answer(context, user_hits)
        result = AgentResult(
            answer=answer,
            intent="USER_SEARCH",
            confidence=max(context.confidence, 0.75),
            raw_users=user_hits,
        ).to_response()
        evaluate_in_background(
            context.trace_id or "",
            context.query,
            answer,
            intent="USER_SEARCH",
            user_hits=user_hits,
        )
        return result

    def _generate_people_answer(self, context: AgentContext, user_hits: List[Dict]) -> str:
        if not self.llm_client:
            names = ", ".join(hit.get("user_id", "unknown") for hit in user_hits[:3])
            return f"Relevant people I found: {names}."

        messages = build_user_search_messages(user_hits, context.query)
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.2,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            names = ", ".join(hit.get("user_id", "unknown") for hit in user_hits[:3])
            return f"Relevant people I found: {names}."

    def _profile_response(self, context: AgentContext, user_id: str) -> Optional[Dict]:
        profile = self.user_store.get_profile(user_id)
        if not profile:
            context.add_step(self.name, "profile_missing", user_id=user_id)
            return None

        answer = f"**{user_id}**\n\n{profile['user_profile']}"
        result = AgentResult(
            answer=answer,
            intent="USER_SEARCH",
            confidence=1.0,
            exact_match=True,
            raw_users=[profile],
        ).to_response()
        evaluate_in_background(
            context.trace_id or "",
            context.query,
            answer,
            intent="USER_SEARCH",
            exact_match=True,
        )
        context.add_step(self.name, "return_profile", user_id=user_id)
        return result
