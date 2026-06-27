"""Document loader for Postgres-backed artifact metadata."""

import json
import logging
from typing import Dict, List, Optional

from langchain_core.documents import Document

from .config import RetrievalConfig
from .document_guard import DocumentGuard
from .metadata_repository import MetadataRepository

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loader for documents from the Postgres metadata store."""

    ALLOWED_FILE_TYPES = {"notebook", "script", "text"}

    def __init__(
        self,
        config: Optional[RetrievalConfig] = None,
        metadata_repository: Optional[MetadataRepository] = None,
    ):
        self.config = config or RetrievalConfig.from_env()
        self.metadata_repository = metadata_repository or MetadataRepository()
        self._workspaces_by_id: Dict[str, Dict] = {}
        self._artifact_counts_by_workspace: Dict[str, int] = {}

    def get_artifacts(self, workspace_id: Optional[str] = None) -> List[Dict]:
        """Get artifacts from Postgres."""
        if not self.metadata_repository.enabled:
            raise RuntimeError("METADATA_DATABASE_URL is required for artifact loading")

        artifacts = self.metadata_repository.list_artifacts(workspace_id)
        if not self._workspaces_by_id:
            self._workspaces_by_id = {
                workspace["workspace_id"]: workspace
                for workspace in self.metadata_repository.list_workspaces()
            }
        if not self._artifact_counts_by_workspace:
            self._artifact_counts_by_workspace = self.metadata_repository.artifact_counts_by_workspace()
        return artifacts

    def load_documents(self, apply_guardrails: bool = True) -> List[Document]:
        artifacts = self.get_artifacts()
        documents = []

        for artifact in artifacts:
            file_type = artifact.get("file_type", artifact.get("type", ""))
            if file_type not in self.ALLOWED_FILE_TYPES:
                continue
            try:
                doc = self._artifact_to_document(artifact)
                if doc:
                    documents.append(doc)
            except Exception as e:
                logger.warning(f"Failed to process artifact {artifact.get('artifact_id')}: {e}")
                continue

        logger.info(f"Loaded {len(documents)} documents from {len(artifacts)} artifacts")

        if apply_guardrails:
            original_count = len(documents)
            documents = DocumentGuard.filter_documents(documents)
            logger.info(f"Applied guardrails: {len(documents)}/{original_count} documents retained")

        return documents

    def _artifact_to_document(self, artifact: Dict) -> Optional[Document]:
        content = self._extract_content(artifact)
        if not content:
            return None

        return Document(
            page_content=content,
            metadata=self._build_metadata(artifact),
        )

    def _extract_content(self, artifact: Dict) -> Optional[str]:
        file_type = artifact.get("file_type", artifact.get("type", ""))
        source_path = artifact.get("capture_source", {}).get("source_path", "")

        if not source_path:
            return artifact.get("content", "")

        try:
            with open(source_path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
        except (OSError, IOError):
            return None

        if file_type == "notebook":
            return self._extract_notebook_content_from_text(content)
        return content

    def _extract_notebook_content_from_text(self, raw: str) -> str:
        try:
            notebook = json.loads(raw)
            cells = notebook.get("cells", [])
            parts = []
            for cell in cells:
                if cell.get("cell_type") in ["code", "markdown"]:
                    source = cell.get("source", [])
                    parts.append("".join(source) if isinstance(source, list) else str(source))
            return "\n\n".join(parts)
        except (json.JSONDecodeError, Exception):
            return raw

    def _build_metadata(self, artifact: Dict) -> Dict:
        metadata = {
            "artifact_id": artifact.get("artifact_id", artifact.get("id", "")),
            "workspace_id": artifact.get("workspace_id", ""),
            "type": artifact.get("file_type", artifact.get("type", "")),
            "path": artifact.get("relative_path", artifact.get("path", "")),
            "size": artifact.get("size_bytes", artifact.get("size", 0)),
            "modified_at": artifact.get("last_modified_at", artifact.get("modified_at", "")),
        }

        if "metadata" in artifact:
            metadata.update(artifact["metadata"])

        metadata.update(self._enrich_workspace_context(artifact))
        return metadata

    def _enrich_workspace_context(self, artifact: Dict) -> Dict:
        workspace_id = artifact.get("workspace_id", "")
        workspace = self._workspaces_by_id.get(workspace_id, {})
        return {
            "workspace_name": workspace.get("workspace_id", workspace_id),
            "workspace_owner": workspace.get("owner", ""),
            "workspace_path": workspace.get("root_path", ""),
            "artifact_count_in_workspace": self._artifact_counts_by_workspace.get(workspace_id, 0),
        }
