"""System metadata specialist agent."""

from __future__ import annotations

from typing import Any, Optional

from ..chatbot.memory import is_system_stats_query
from .types import AgentContext, AgentResult


class MetadataAgent:
    """Answers count and inventory questions from the metadata repository."""

    name = "metadata"

    def __init__(self, metadata_repository: Any):
        self.metadata_repository = metadata_repository

    def run(self, context: AgentContext) -> Optional[AgentResult]:
        if context.intent != "SYSTEM_STATS" and not is_system_stats_query(context.query):
            context.add_step(self.name, "pass")
            return None

        context.add_step(self.name, "load_system_metadata")
        answer = self._answer(context.query)
        return AgentResult(
            answer=answer,
            intent="SYSTEM_STATS",
            confidence=max(context.confidence, 0.95),
        )

    def _answer(self, query: str) -> str:
        if not getattr(self.metadata_repository, "enabled", False):
            return "Workspace metadata is not available right now."

        workspaces = self.metadata_repository.list_workspaces()
        artifacts = self.metadata_repository.list_artifacts()
        notebooks = [artifact for artifact in artifacts if artifact.get("file_type") == "notebook"]
        scripts = [artifact for artifact in artifacts if artifact.get("file_type") == "script"]

        normalized = query.lower()
        if "artifact" in normalized:
            return f"There are {len(artifacts)} artifacts currently indexed across {len(workspaces)} workspaces."
        if "notebook" in normalized:
            return f"There are {len(notebooks)} notebooks currently indexed across {len(workspaces)} workspaces."
        if "script" in normalized:
            return f"There are {len(scripts)} scripts currently indexed across {len(workspaces)} workspaces."
        return f"There are {len(workspaces)} workspaces currently indexed in the system."
