from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class IngestionStatus(str, Enum):
    NEW = "new"
    UNCHANGED = "unchanged"
    UPDATED = "updated"
    SKIPPED = "skipped"
    ERROR = "error"

    def __str__(self) -> str:
        return self.value


class FileType(str, Enum):
    NOTEBOOK = "notebook"
    SCRIPT = "script"
    TEXT = "text"
    DOCUMENT = "document"
    BINARY = "binary"
    IMAGE = "image"
    ARCHIVE = "archive"
    ENV = "env"
    UNSUPPORTED = "unsupported"


@dataclass
class Workspace:
    workspace_id: str
    owner: str
    root_path: str
    file_count: int = 0
    last_ingested_at: Optional[datetime] = None
    status: str = "pending"
    source_coverage: Dict[str, int] = field(default_factory=dict)
    notes: Optional[str] = None


@dataclass
class FileArtifact:
    artifact_id: str
    workspace_id: str
    relative_path: str
    file_name: str
    file_type: FileType
    mime_type: Optional[str] = None
    size_bytes: int = 0
    last_modified_at: Optional[datetime] = None
    ingestion_status: IngestionStatus = IngestionStatus.NEW
    classification: Dict[str, Any] = field(default_factory=dict)
    content_hash: Optional[str] = None
    capture_source: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotebookDocument:
    document_id: str
    artifact_id: str
    notebook_title: Optional[str] = None
    kernel_language: Optional[str] = None
    cells_count: Optional[int] = None
    extracted_tools: List[str] = field(default_factory=list)
    database_targets: List[str] = field(default_factory=list)
    table_references: List[str] = field(default_factory=list)
    notebook_summary: Optional[str] = None
    source_snippets: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class IngestionRun:
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    run_type: str = "initial"
    workspace_scope: Optional[List[str]] = None
    status: str = "running"
    summary: Dict[str, int] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionAudit:
    audit_id: str
    artifact_id: Optional[str]
    workspace_id: Optional[str]
    run_id: str
    decision: str
    reason: str
    matched_pattern: Optional[str] = None
    metadata_snapshot: Optional[Dict[str, Any]] = None
