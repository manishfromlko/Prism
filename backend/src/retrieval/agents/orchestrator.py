"""Top-level multi-agent orchestrator for chatbot turns."""

from __future__ import annotations

import logging
import uuid
from typing import Dict, Optional

from ...observability import mlflow_chat_trace, record_mlflow_chat_output
from ..chatbot.engine import ChatEngine
from .artifacts import ArtifactAgent
from .critic import CriticAgent
from .docs import DocsAgent
from .memory import MemoryAgent
from .metadata import MetadataAgent
from .people import PeopleProfileAgent
from .synthesis import SynthesisAgent
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
        self.synthesis_agent = SynthesisAgent(chat_engine.client, chat_engine.llm_model)
        self.critic_agent = CriticAgent()
        self.memory_agent = MemoryAgent()
        self.metadata_agent = MetadataAgent(chat_engine.metadata_repository)
        self.artifact_agent = ArtifactAgent(
            artifact_retriever=chat_engine.artifact_retriever,
            synthesis_agent=self.synthesis_agent,
        )
        self.docs_agent = DocsAgent(
            doc_retriever=chat_engine.doc_retriever,
            synthesis_agent=self.synthesis_agent,
        )
        self.people_agent = PeopleProfileAgent(
            user_store=chat_engine.user_store,
            user_resolver=chat_engine.user_resolver,
            user_retriever=chat_engine.user_retriever,
            synthesis_agent=self.synthesis_agent,
        )

    def run(
        self,
        query: str,
        history: Optional[list[dict]] = None,
        session_id: Optional[str] = None,
    ) -> Dict:
        with mlflow_chat_trace(query=query, history=history, session_id=session_id) as mlflow_span:
            result = self._run_once(query=query, history=history, session_id=session_id)
            record_mlflow_chat_output(mlflow_span, result)
            return result

    def _run_once(
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
        context.intent = intent
        context.confidence = confidence
        context.add_step(
            self.name,
            "classify_intent",
            intent=intent,
            confidence=round(confidence, 4),
        )

        memory_result = self.memory_agent.run(context)
        if memory_result:
            return self._finalize_agent_result(memory_result.to_response(), context)

        metadata_result = self.metadata_agent.run(context)
        if metadata_result:
            return self._finalize_agent_result(metadata_result.to_response(), context)

        if intent == "USER_SEARCH":
            people_result = self.people_agent.run(context)
            if people_result:
                return self._finalize_agent_result(people_result, context)

        if intent == "ARTIFACT_SEARCH":
            context.search_query = self.chat_engine.rewriter.rewrite(
                context.query,
                trace_id=context.trace_id,
            )
            context.add_step(self.name, "rewrite_query", search_query=context.search_query)
            artifact_result = self.artifact_agent.run(context)
            if artifact_result:
                return self._finalize_agent_result(artifact_result, context)

        if intent == "DOC_QA":
            context.search_query = self.chat_engine.rewriter.rewrite(
                context.query,
                trace_id=context.trace_id,
            )
            context.add_step(self.name, "rewrite_query", search_query=context.search_query)
            docs_result = self.docs_agent.run(context)
            if docs_result:
                return self._finalize_agent_result(docs_result, context)

            context.search_query = self.chat_engine.rewriter.rewrite(
                context.query,
                trace_id=context.trace_id,
            )
            context.add_step(self.name, "rewrite_query", search_query=context.search_query)
            people_result = self.people_agent.semantic_search(context)
            if people_result:
                return self._finalize_agent_result(people_result, context)

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

    def _finalize_agent_result(self, result: Dict, context: AgentContext) -> Dict:
        result = self.critic_agent.review(context, result)
        result["trace_id"] = context.trace_id
        result["agent_mode"] = "orchestrated"
        result["agent_steps"] = self._serialize_steps(context)
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
