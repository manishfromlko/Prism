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

    def add_step(self, agent: str, action: str, **details: Any) -> None:
        self.steps.append(AgentStep(agent=agent, action=action, details=details))

    def add_evidence(self, result: AgentToolResult) -> None:
        self.evidence.append(result)
