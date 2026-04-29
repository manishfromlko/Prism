"""Document loader for ingestion catalog artifacts."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.documents import Document

from .config import RetrievalConfig
from .document_guard import DocumentGuard

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loader for documents from the ingestion catalog."""

    def __init__(self, catalog_path: str, config: Optional[RetrievalConfig] = None):
        """Initialize the document loader.

        Args:
            catalog_path: Path to the ingestion catalog JSON file
            config: Retrieval configuration (optional)
        """
        self.catalog_path = Path(catalog_path)
        self.config = config or RetrievalConfig()
        self._catalog: Optional[Dict] = None

    def load_catalog(self, force: bool = False) -> Dict:
        """Load the ingestion catalog from JSON file. Cached after first load.

        Args:
            force: Re-read from disk even if already cached
        """
        if self._catalog is not None and not force:
            return self._catalog

        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog file not found: {self.catalog_path}")

        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                self._catalog = json.load(f)
            logger.info(f"Loaded catalog with {len(self._catalog.get('artifacts', {}))} artifacts")
            return self._catalog
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            raise

    def get_artifacts(self) -> List[Dict]:
        """Get all artifacts from the catalog.

        Returns:
            List of artifact dictionaries
        """
        if not self._catalog:
            self.load_catalog()

        return list(self._catalog.get('artifacts', {}).values())

    # Only index these file types — CSVs, binaries, archives, etc. are not useful
    # for user profiling and can contain enormous amounts of noisy numerical data.
    ALLOWED_FILE_TYPES = {"notebook", "script", "text"}

    def load_documents(self, apply_guardrails: bool = True) -> List[Document]:
        """Load all artifacts as Langchain documents.

        Args:
            apply_guardrails: Whether to apply document filtering

        Returns:
            List of Document objects
        """
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
                logger.warning(f"Failed to process artifact {artifact.get('id')}: {e}")
                continue

        logger.info(f"Loaded {len(documents)} documents from {len(artifacts)} artifacts")

        # Apply guardrails if requested
        if apply_guardrails:
            original_count = len(documents)
            documents = DocumentGuard.filter_documents(documents)
            logger.info(f"Applied guardrails: {len(documents)}/{original_count} documents retained")

        return documents

    def _artifact_to_document(self, artifact: Dict) -> Optional[Document]:
        """Convert an artifact to a Langchain document.

        Args:
            artifact: Artifact dictionary from catalog

        Returns:
            Document object or None if invalid
        """
        # Extract content
        content = self._extract_content(artifact)
        if not content:
            return None

        # Build metadata
        metadata = self._build_metadata(artifact)

        return Document(
            page_content=content,
            metadata=metadata
        )

    def _extract_content(self, artifact: Dict) -> Optional[str]:
        """Extract text content from artifact.

        Args:
            artifact: Artifact dictionary

        Returns:
            Extracted text content
        """
        file_type = artifact.get('file_type', artifact.get('type', ''))
        source_path = artifact.get('capture_source', {}).get('source_path', '')

        if not source_path:
            return artifact.get('content', '')

        try:
            content = open(source_path, 'r', encoding='utf-8', errors='ignore').read()
        except (OSError, IOError):
            return None

        if file_type == 'notebook':
            return self._extract_notebook_content_from_text(content)

        return content

    def _extract_notebook_content_from_text(self, raw: str) -> str:
        """Extract cell text from raw notebook JSON string."""
        try:
            notebook = json.loads(raw)
            cells = notebook.get('cells', [])
            parts = []
            for cell in cells:
                if cell.get('cell_type') in ['code', 'markdown']:
                    source = cell.get('source', [])
                    parts.append(''.join(source) if isinstance(source, list) else str(source))
            return '\n\n'.join(parts)
        except (json.JSONDecodeError, Exception):
            return raw

    def _extract_notebook_content(self, artifact: Dict) -> str:
        """Extract content from Jupyter notebook artifact dict (legacy path)."""
        content = artifact.get('content', '')
        if not content:
            return ''
        return self._extract_notebook_content_from_text(content)

    def _build_metadata(self, artifact: Dict) -> Dict:
        """Build metadata dictionary for the document.

        Args:
            artifact: Artifact dictionary

        Returns:
            Metadata dictionary
        """
        metadata = {
            'artifact_id': artifact.get('artifact_id', artifact.get('id', '')),
            'workspace_id': artifact.get('workspace_id', ''),
            'type': artifact.get('file_type', artifact.get('type', '')),
            'path': artifact.get('relative_path', artifact.get('path', '')),
            'size': artifact.get('size_bytes', artifact.get('size', 0)),
            'modified_at': artifact.get('last_modified_at', artifact.get('modified_at', '')),
        }

        # Add any additional metadata from artifact
        if 'metadata' in artifact:
            metadata.update(artifact['metadata'])

        # Enrich with workspace context
        metadata.update(self._enrich_workspace_context(artifact))

        return metadata

    def _enrich_workspace_context(self, artifact: Dict) -> Dict:
        """Enrich metadata with workspace-level context.

        Args:
            artifact: Artifact dictionary

        Returns:
            Additional metadata
        """
        workspace_id = artifact.get('workspace_id', '')
        if not workspace_id or not self._catalog:
            return {}

        workspaces = self._catalog.get('workspaces', {})
        workspace = workspaces.get(workspace_id, {})

        return {
            'workspace_name': workspace.get('workspace_id', workspace.get('name', '')),
            'workspace_owner': workspace.get('owner', ''),
            'workspace_path': workspace.get('root_path', workspace.get('path', '')),
            'artifact_count_in_workspace': len([
                a for a in self._catalog.get('artifacts', {}).values()
                if a.get('workspace_id') == workspace_id
            ]),
        }