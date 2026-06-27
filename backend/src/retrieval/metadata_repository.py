from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.ingestion.metadata_store import PostgresMetadataStore


class MetadataRepository:
    """Read-side metadata repository for workspace and artifact API views."""

    def __init__(self) -> None:
        self.store = PostgresMetadataStore.from_env()
        if self.store:
            self.store.initialize()

    @property
    def enabled(self) -> bool:
        return self.store is not None

    def list_workspaces(self) -> List[Dict[str, Any]]:
        if not self.store:
            return []
        return self.store.list_workspaces()

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        if not self.store:
            return None
        return self.store.get_workspace(workspace_id)

    def artifact_counts_by_workspace(self) -> Dict[str, int]:
        if not self.store:
            return {}
        return self.store.artifact_counts_by_workspace()

    def list_artifacts(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.store:
            return []
        return self.store.list_artifacts(workspace_id)
