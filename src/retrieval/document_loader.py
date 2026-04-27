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

    def load_catalog(self) -> Dict:
        """Load the ingestion catalog from JSON file.

        Returns:
            Catalog dictionary
        """
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
        # For notebooks, extract cell contents
        if artifact.get('type') == 'notebook':
            return self._extract_notebook_content(artifact)

        # For scripts, use the content directly
        elif artifact.get('type') in ['python', 'script']:
            return artifact.get('content', '')

        # For other types, try content field
        return artifact.get('content', '')

    def _extract_notebook_content(self, artifact: Dict) -> str:
        """Extract content from Jupyter notebook.

        Args:
            artifact: Notebook artifact

        Returns:
            Concatenated cell contents
        """
        content = artifact.get('content', '')
        if not content:
            return ''

        try:
            # Parse notebook JSON
            notebook = json.loads(content)
            cells = notebook.get('cells', [])

            # Extract code and markdown cells
            text_parts = []
            for cell in cells:
                if cell.get('cell_type') in ['code', 'markdown']:
                    source = cell.get('source', [])
                    if isinstance(source, list):
                        text_parts.append(''.join(source))
                    else:
                        text_parts.append(str(source))

            return '\n\n'.join(text_parts)
        except json.JSONDecodeError:
            logger.warning(f"Invalid notebook JSON for artifact {artifact.get('id')}")
            return content

    def _build_metadata(self, artifact: Dict) -> Dict:
        """Build metadata dictionary for the document.

        Args:
            artifact: Artifact dictionary

        Returns:
            Metadata dictionary
        """
        metadata = {
            'artifact_id': artifact.get('id', ''),
            'workspace_id': artifact.get('workspace_id', ''),
            'type': artifact.get('type', ''),
            'path': artifact.get('path', ''),
            'size': artifact.get('size', 0),
            'modified_at': artifact.get('modified_at', ''),
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
            'workspace_name': workspace.get('name', ''),
            'workspace_owner': workspace.get('owner', ''),
            'workspace_path': workspace.get('path', ''),
            'artifact_count_in_workspace': len([
                a for a in self._catalog.get('artifacts', {}).values()
                if a.get('workspace_id') == workspace_id
            ]),
        }