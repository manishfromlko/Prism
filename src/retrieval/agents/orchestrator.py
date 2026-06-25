"""Top-level multi-agent orchestrator for chatbot turns."""

from __future__ import annotations

import logging
import uuid
from typing import Dict, Optional

from ..chatbot.engine import ChatEngine
from .people import PeopleProfileAgent
from .types import AgentContext

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Coordinates specialist agents for a chat turn.

    The orchestrator owns per-turn state and delegates to specialist agents when
    a deterministic path is available. It falls back to ChatEngine for flows
    that have not yet been migrated.
    """

    name = "orchestrator"

    def __init__(
        self,
        chat_engine: ChatEngine,
        max_steps: int = 4,
        planner_enabled: bool = False,
    ):
        self.chat_engine = chat_engine
        self.max_steps = max_steps
        self.planner_enabled = planner_enabled
        self.people_agent = PeopleProfileAgent(
            user_store=chat_engine.user_store,
            user_resolver=chat_engine.user_resolver,
        )

    def run(
        self,
        query: str,
        history: Optional[list[dict]] = None,
        session_id: Optional[str] = None,
    ) -> Dict:
        context = AgentContext(
            query=query,
            history=history or [],
            trace_id=str(uuid.uuid4()),
            session_id=session_id,
            max_steps=self.max_steps,
            planner_enabled=self.planner_enabled,
        )
        context.add_step(
            self.name,
            "start",
            mode="orchestrated",
            planner_enabled=self.planner_enabled,
            max_steps=self.max_steps,
        )

        classification = self.chat_engine.classifier.classify(
            context.query,
            trace_id=context.trace_id,
        )
        intent = classification["intent"]
        confidence = classification["confidence"]
        context.add_step(
            self.name,
            "classify_intent",
            intent=intent,
            confidence=round(confidence, 4),
        )

        if intent == "USER_SEARCH":
            people_result = self.people_agent.run(context)
            if people_result:
                people_result["trace_id"] = context.trace_id
                people_result["agent_mode"] = "orchestrated"
                people_result["agent_steps"] = self._serialize_steps(context)
                return people_result

            context.add_step(
                self.name,
                "fallback_to_legacy_chat_engine",
                reason="people_agent_no_result",
            )

        result = self.chat_engine.chat(
            query=context.query,
            history=context.history,
            session_id=context.session_id,
        )

        context.trace_id = result.get("trace_id")
        context.add_step(
            self.name,
            "delegate_to_legacy_chat_engine",
            intent=result.get("intent"),
            confidence=result.get("confidence"),
            exact_match=result.get("exact_match", False),
        )

        result["agent_mode"] = "orchestrated"
        result["agent_steps"] = self._serialize_steps(context)
        logger.info(
            "Orchestrator completed chat turn: intent=%s steps=%s",
            result.get("intent"),
            len(context.steps),
        )
        return result

    @staticmethod
    def _serialize_steps(context: AgentContext) -> list[dict]:
        return [
            {
                "agent": step.agent,
                "action": step.action,
                "status": step.status,
                "details": step.details,
            }
            for step in context.steps
        ]
