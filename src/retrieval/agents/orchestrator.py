"""Top-level multi-agent orchestrator for chatbot turns."""

from __future__ import annotations

import logging
from typing import Dict, Optional

from ..chatbot.engine import ChatEngine
from .types import AgentContext

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Coordinates specialist agents for a chat turn.

    Feature 2 intentionally preserves legacy behavior by delegating to the
    existing ChatEngine. Later feature slices will replace the delegate with
    specialist agents while keeping this public run() contract stable.
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

    def run(
        self,
        query: str,
        history: Optional[list[dict]] = None,
        session_id: Optional[str] = None,
    ) -> Dict:
        context = AgentContext(
            query=query,
            history=history or [],
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
        result["agent_steps"] = [
            {
                "agent": step.agent,
                "action": step.action,
                "status": step.status,
                "details": step.details,
            }
            for step in context.steps
        ]
        logger.info(
            "Orchestrator completed chat turn: intent=%s steps=%s",
            result.get("intent"),
            len(context.steps),
        )
        return result
