"""Shared types for the multi-agent chatbot runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentStep:
    """One orchestrator or specialist-agent action."""

    agent: str
    action: str
    status: str = "completed"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentToolResult:
    """Typed envelope for future retriever/tool calls."""

    tool_name: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Canonical output returned by a specialist agent."""

    answer: str
    intent: str
    confidence: float
    handled: bool = True
    exact_match: bool = False
    raw_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    raw_users: List[Dict[str, Any]] = field(default_factory=list)
    raw_docs: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_response(self) -> Dict[str, Any]:
        from ..chatbot.formatter import format_response

        result = format_response(
            answer=self.answer,
            intent=self.intent,
            confidence=self.confidence,
            raw_artifacts=self.raw_artifacts,
            raw_users=self.raw_users,
            raw_docs=self.raw_docs,
            exact_match=self.exact_match,
        )
        result.update(self.metadata)
        return result


@dataclass
class AgentContext:
    """Per-turn state shared by the orchestrator and specialist agents."""

    query: str
    history: List[Dict[str, str]] = field(default_factory=list)
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    max_steps: int = 4
    planner_enabled: bool = False
    steps: List[AgentStep] = field(default_factory=list)
    evidence: List[AgentToolResult] = field(default_factory=list)
    intent: Optional[str] = None
    confidence: float = 0.0
    search_query: Optional[str] = None

    def add_step(self, agent: str, action: str, **details: Any) -> None:
        self.steps.append(AgentStep(agent=agent, action=action, details=details))

    def add_evidence(self, result: AgentToolResult) -> None:
        self.evidence.append(result)
