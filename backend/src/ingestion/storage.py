from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import FileArtifact, IngestionAudit, IngestionRun, Workspace


class Storage:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.catalog_path = self.base_path / "ingestion_catalog.json"
        self.audit_path = self.base_path / "ingestion_audit.json"
        self._catalog: Dict[str, Any] = {}
        self._audit: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.catalog_path.exists():
            try:
                with self.catalog_path.open("r", encoding="utf-8") as handle:
                    self._catalog = json.load(handle)
            except (OSError, ValueError):
                self._catalog = {}
        if self.audit_path.exists():
            try:
                with self.audit_path.open("r", encoding="utf-8") as handle:
                    self._audit = json.load(handle)
            except (OSError, ValueError):
                self._audit = []

    def save(self) -> None:
        self.base_path.mkdir(parents=True, exist_ok=True)
        with self.catalog_path.open("w", encoding="utf-8") as handle:
            json.dump(self._catalog, handle, indent=2)
        with self.audit_path.open("w", encoding="utf-8") as handle:
            json.dump(self._audit, handle, indent=2)

    def write_workspace(self, workspace: Workspace) -> None:
        self._catalog.setdefault("workspaces", {})[workspace.workspace_id] = {
            "workspace_id": workspace.workspace_id,
            "owner": workspace.owner,
            "root_path": workspace.root_path,
            "file_count": workspace.file_count,
            "last_ingested_at": workspace.last_ingested_at.isoformat()
            if workspace.last_ingested_at
            else None,
            "status": workspace.status,
            "source_coverage": workspace.source_coverage,
            "notes": workspace.notes,
        }

    def write_artifact(self, artifact: FileArtifact) -> None:
        self._catalog.setdefault("artifacts", {})[artifact.artifact_id] = {
            "artifact_id": artifact.artifact_id,
            "workspace_id": artifact.workspace_id,
            "relative_path": artifact.relative_path,
            "file_name": artifact.file_name,
            "file_type": artifact.file_type.value,
            "mime_type": artifact.mime_type,
            "size_bytes": artifact.size_bytes,
            "last_modified_at": artifact.last_modified_at.isoformat()
            if artifact.last_modified_at
            else None,
            "ingestion_status": artifact.ingestion_status.value,
            "classification": artifact.classification,
            "content_hash": artifact.content_hash,
            "capture_source": artifact.capture_source,
        }

    def write_audit(self, audit: IngestionAudit) -> None:
        self._audit.append({
            "audit_id": audit.audit_id,
            "artifact_id": audit.artifact_id,
            "workspace_id": audit.workspace_id,
            "run_id": audit.run_id,
            "decision": audit.decision,
            "reason": audit.reason,
            "matched_pattern": audit.matched_pattern,
            "metadata_snapshot": audit.metadata_snapshot,
        })

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        return self._catalog.get("workspaces", {}).get(workspace_id)

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        return self._catalog.get("artifacts", {}).get(artifact_id)

    def get_artifact_hash(self, artifact_id: str) -> Optional[str]:
        artifact = self._catalog.get("artifacts", {}).get(artifact_id)
        return artifact.get("content_hash") if artifact else None

    def get_workspace_last_ingested(self, workspace_id: str) -> Optional[datetime]:
        workspace = self._catalog.get("workspaces", {}).get(workspace_id)
        if workspace and workspace.get("last_ingested_at"):
            return datetime.fromisoformat(workspace["last_ingested_at"])
        return None

    def summary(self) -> Dict[str, Any]:
        audit_summary = {}
        for audit in self._audit:
            decision = audit.get("decision", "unknown")
            audit_summary[decision] = audit_summary.get(decision, 0) + 1

        # Determine health
        error_count = audit_summary.get("error", 0)
        skipped_count = audit_summary.get("skipped", 0)
        if error_count > 0:
            health = "failed"
        elif skipped_count > 0:
            health = "degraded"
        else:
            health = "ok"

        artifact_count = sum(
            1
            for artifact in self._catalog.get("artifacts", {}).values()
            if artifact.get("ingestion_status") != "skipped"
        )

        return {
            "workspaces": len(self._catalog.get("workspaces", {})),
            "artifacts": artifact_count,
            "audit_records": len(self._audit),
            "audit_summary": audit_summary,
            "pipeline_health": health,
        }
