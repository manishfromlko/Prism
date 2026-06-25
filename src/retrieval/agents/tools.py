"""Typed retrieval tools used by specialist agents and the planner."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..profiling import WorkspaceProfiler
from .types import AgentToolResult


def _confidence_from_count(count: int, top_k: int) -> float:
    if top_k <= 0 or count <= 0:
        return 0.0
    return round(min(1.0, count / top_k), 3)


class RetrievalToolbelt:
    """Thin typed wrappers around existing retrievers and profile services."""

    def __init__(
        self,
        doc_retriever: Any,
        artifact_retriever: Any,
        user_retriever: Any,
        profiler: Optional[WorkspaceProfiler] = None,
    ):
        self.doc_retriever = doc_retriever
        self.artifact_retriever = artifact_retriever
        self.user_retriever = user_retriever
        self.profiler = profiler

    def search_platform_docs(self, query: str, top_k: int = 5) -> AgentToolResult:
        items = self.doc_retriever.retrieve(query, top_k=top_k)
        return AgentToolResult(
            tool_name="search_platform_docs",
            items=items,
            confidence=_confidence_from_count(len(items), top_k),
            metadata={"query": query, "top_k": top_k},
        )

    def search_artifacts(self, query: str, top_k: int = 5) -> AgentToolResult:
        items = self.artifact_retriever.retrieve(query, top_k=top_k)
        return AgentToolResult(
            tool_name="search_artifacts",
            items=items,
            confidence=_confidence_from_count(len(items), top_k),
            metadata={"query": query, "top_k": top_k},
        )

    def search_user_profiles(self, query: str, top_k: int = 5) -> AgentToolResult:
        items = self.user_retriever.retrieve(query, top_k=top_k)
        return AgentToolResult(
            tool_name="search_user_profiles",
            items=items,
            confidence=_confidence_from_count(len(items), top_k),
            metadata={"query": query, "top_k": top_k},
        )

    def get_workspace_profile(self, workspace_id: str) -> AgentToolResult:
        if not self.profiler:
            return AgentToolResult(
                tool_name="get_workspace_profile",
                items=[],
                confidence=0.0,
                metadata={"workspace_id": workspace_id, "available": False},
            )

        profile: Dict[str, Any] = self.profiler.profile_workspace(workspace_id)
        found = profile.get("artifact_count", 0) > 0
        return AgentToolResult(
            tool_name="get_workspace_profile",
            items=[profile] if found else [],
            confidence=1.0 if found else 0.0,
            metadata={"workspace_id": workspace_id, "available": True},
        )
