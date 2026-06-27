from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from .models import FileArtifact, IngestionAudit, Workspace

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional when DATABASE_URL is unset
    psycopg = None
    dict_row = None


def _json(data: Any) -> str:
    return json.dumps(data or {})


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class PostgresMetadataStore:
    """Postgres-backed metadata registry for workspaces and file artifacts."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("METADATA_DATABASE_URL")
        if not self.database_url:
            raise ValueError("METADATA_DATABASE_URL is not configured")
        if psycopg is None:
            raise RuntimeError("psycopg is required when METADATA_DATABASE_URL is configured")

    @classmethod
    def from_env(cls) -> Optional["PostgresMetadataStore"]:
        database_url = os.getenv("METADATA_DATABASE_URL")
        return cls(database_url) if database_url else None

    @contextmanager
    def connect(self) -> Iterator[Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            yield conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    file_count INTEGER NOT NULL DEFAULT 0,
                    last_ingested_at TIMESTAMPTZ,
                    status TEXT NOT NULL DEFAULT 'pending',
                    source_coverage JSONB NOT NULL DEFAULT '{}'::jsonb,
                    notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id)
                        ON DELETE CASCADE,
                    relative_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    mime_type TEXT,
                    size_bytes BIGINT NOT NULL DEFAULT 0,
                    last_modified_at TIMESTAMPTZ,
                    ingestion_status TEXT NOT NULL,
                    classification JSONB NOT NULL DEFAULT '{}'::jsonb,
                    content_hash TEXT,
                    capture_source JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_audits (
                    audit_id TEXT PRIMARY KEY,
                    artifact_id TEXT,
                    workspace_id TEXT,
                    run_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    matched_pattern TEXT,
                    metadata_snapshot JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_workspace_id ON artifacts(workspace_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_file_type ON artifacts(file_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifacts_content_hash ON artifacts(content_hash)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ingestion_audits_workspace_id ON ingestion_audits(workspace_id)"
            )
            conn.commit()

    def reset(self) -> None:
        with self.connect() as conn:
            conn.execute("TRUNCATE ingestion_audits, artifacts, workspaces RESTART IDENTITY CASCADE")
            conn.commit()

    def upsert_workspace(self, workspace: Workspace) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO workspaces (
                    workspace_id, owner, root_path, file_count, last_ingested_at,
                    status, source_coverage, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (workspace_id) DO UPDATE SET
                    owner = EXCLUDED.owner,
                    root_path = EXCLUDED.root_path,
                    file_count = EXCLUDED.file_count,
                    last_ingested_at = EXCLUDED.last_ingested_at,
                    status = EXCLUDED.status,
                    source_coverage = EXCLUDED.source_coverage,
                    notes = EXCLUDED.notes,
                    updated_at = now()
                """,
                (
                    workspace.workspace_id,
                    workspace.owner,
                    workspace.root_path,
                    workspace.file_count,
                    workspace.last_ingested_at,
                    workspace.status,
                    _json(workspace.source_coverage),
                    workspace.notes,
                ),
            )
            conn.commit()

    def upsert_artifact(self, artifact: FileArtifact) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, workspace_id, relative_path, file_name, file_type,
                    mime_type, size_bytes, last_modified_at, ingestion_status,
                    classification, content_hash, capture_source
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
                ON CONFLICT (artifact_id) DO UPDATE SET
                    workspace_id = EXCLUDED.workspace_id,
                    relative_path = EXCLUDED.relative_path,
                    file_name = EXCLUDED.file_name,
                    file_type = EXCLUDED.file_type,
                    mime_type = EXCLUDED.mime_type,
                    size_bytes = EXCLUDED.size_bytes,
                    last_modified_at = EXCLUDED.last_modified_at,
                    ingestion_status = EXCLUDED.ingestion_status,
                    classification = EXCLUDED.classification,
                    content_hash = EXCLUDED.content_hash,
                    capture_source = EXCLUDED.capture_source,
                    updated_at = now()
                """,
                (
                    artifact.artifact_id,
                    artifact.workspace_id,
                    artifact.relative_path,
                    artifact.file_name,
                    artifact.file_type.value,
                    artifact.mime_type,
                    artifact.size_bytes,
                    artifact.last_modified_at,
                    artifact.ingestion_status.value,
                    _json(artifact.classification),
                    artifact.content_hash,
                    _json(artifact.capture_source),
                ),
            )
            conn.commit()

    def upsert_artifact_status(self, artifact_id: str, ingestion_status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE artifacts
                SET ingestion_status = %s, updated_at = now()
                WHERE artifact_id = %s
                """,
                (ingestion_status, artifact_id),
            )
            conn.commit()

    def insert_audit(self, audit: IngestionAudit) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_audits (
                    audit_id, artifact_id, workspace_id, run_id, decision,
                    reason, matched_pattern, metadata_snapshot
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (audit_id) DO UPDATE SET
                    decision = EXCLUDED.decision,
                    reason = EXCLUDED.reason,
                    matched_pattern = EXCLUDED.matched_pattern,
                    metadata_snapshot = EXCLUDED.metadata_snapshot
                """,
                (
                    audit.audit_id,
                    audit.artifact_id,
                    audit.workspace_id,
                    audit.run_id,
                    audit.decision,
                    audit.reason,
                    audit.matched_pattern,
                    _json(audit.metadata_snapshot),
                ),
            )
            conn.commit()

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspaces WHERE workspace_id = %s",
                (workspace_id,),
            ).fetchone()
        return self._workspace_row(row) if row else None

    def list_workspaces(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM workspaces ORDER BY workspace_id"
            ).fetchall()
        return [self._workspace_row(row) for row in rows]

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM artifacts WHERE artifact_id = %s",
                (artifact_id,),
            ).fetchone()
        return self._artifact_row(row) if row else None

    def list_artifacts(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            if workspace_id:
                rows = conn.execute(
                    "SELECT * FROM artifacts WHERE workspace_id = %s ORDER BY relative_path",
                    (workspace_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM artifacts ORDER BY workspace_id, relative_path"
                ).fetchall()
        return [self._artifact_row(row) for row in rows]

    def get_artifact_hash(self, artifact_id: str) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT content_hash FROM artifacts WHERE artifact_id = %s",
                (artifact_id,),
            ).fetchone()
        return row["content_hash"] if row else None

    def artifact_counts_by_workspace(self) -> Dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT workspace_id, count(*) AS artifact_count
                FROM artifacts
                WHERE ingestion_status <> 'skipped'
                GROUP BY workspace_id
                """
            ).fetchall()
        return {row["workspace_id"]: int(row["artifact_count"]) for row in rows}

    def export_catalog(self) -> Dict[str, Any]:
        return {
            "workspaces": {row["workspace_id"]: row for row in self.list_workspaces()},
            "artifacts": {row["artifact_id"]: row for row in self.list_artifacts()},
        }

    def _workspace_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "workspace_id": row["workspace_id"],
            "owner": row["owner"],
            "root_path": row["root_path"],
            "file_count": row["file_count"],
            "last_ingested_at": _iso(row["last_ingested_at"]),
            "status": row["status"],
            "source_coverage": row["source_coverage"] or {},
            "notes": row["notes"],
        }

    def _artifact_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "artifact_id": row["artifact_id"],
            "workspace_id": row["workspace_id"],
            "relative_path": row["relative_path"],
            "file_name": row["file_name"],
            "file_type": row["file_type"],
            "mime_type": row["mime_type"],
            "size_bytes": row["size_bytes"],
            "last_modified_at": _iso(row["last_modified_at"]),
            "ingestion_status": row["ingestion_status"],
            "classification": row["classification"] or {},
            "content_hash": row["content_hash"],
            "capture_source": row["capture_source"] or {},
        }
