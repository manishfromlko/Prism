"""Guardrails for document processing and filtering."""

import logging
import re
from typing import Dict, List, Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentGuard:
    """Guardrails for filtering and sanitizing documents."""

    # Patterns for sensitive content
    SENSITIVE_PATTERNS = [
        re.compile(r'password\s*[:=]\s*\S+', re.IGNORECASE),
        re.compile(r'secret\s*[:=]\s*\S+', re.IGNORECASE),
        re.compile(r'api[_-]?key\s*[:=]\s*\S+', re.IGNORECASE),
        re.compile(r'token\s*[:=]\s*\S+', re.IGNORECASE),
        re.compile(r'private[_-]?key', re.IGNORECASE),
        re.compile(r'\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b'),  # Credit cards
        re.compile(r'\b\d{3}[\s\-]\d{2}[\s\-]\d{4}\b'),  # SSN
    ]

    # Unsupported content types for vector search
    UNSUPPORTED_TYPES = {
        'binary',
        'executable',
        'image',
        'video',
        'audio',
        'archive',
    }

    @classmethod
    def filter_documents(cls, documents: List[Document]) -> List[Document]:
        """Filter documents based on guardrail rules.

        Args:
            documents: List of documents to filter

        Returns:
            Filtered list of documents
        """
        filtered = []
        rejected = []

        for doc in documents:
            if cls._should_include_document(doc):
                filtered.append(doc)
            else:
                rejected.append(doc)

        logger.info(f"Filtered {len(filtered)} documents, rejected {len(rejected)}")
        return filtered

    @classmethod
    def _should_include_document(cls, document: Document) -> bool:
        """Check if a document should be included.

        Args:
            document: Document to check

        Returns:
            True if document should be included
        """
        metadata = document.metadata

        # Check content type
        content_type = metadata.get('type', '').lower()
        if content_type in cls.UNSUPPORTED_TYPES:
            logger.debug(f"Rejected document {metadata.get('artifact_id')}: unsupported type {content_type}")
            return False

        # Check for sensitive content
        if cls._contains_sensitive_content(document.page_content):
            logger.debug(f"Rejected document {metadata.get('artifact_id')}: contains sensitive content")
            return False

        # Check file path for sensitive patterns
        file_path = metadata.get('path', '').lower()
        if any(pattern in file_path for pattern in ['.env', 'secret', 'key', 'credential']):
            logger.debug(f"Rejected document {metadata.get('artifact_id')}: sensitive file path")
            return False

        return True

    @classmethod
    def _contains_sensitive_content(cls, content: str) -> bool:
        """Check if content contains sensitive information.

        Args:
            content: Text content to check

        Returns:
            True if sensitive content detected
        """
        for pattern in cls.SENSITIVE_PATTERNS:
            if pattern.search(content):
                return True
        return False

    @classmethod
    def sanitize_document(cls, document: Document) -> Document:
        """Sanitize document content by removing sensitive information.

        Args:
            document: Document to sanitize

        Returns:
            Sanitized document
        """
        content = document.page_content

        # Remove sensitive patterns
        for pattern in cls.SENSITIVE_PATTERNS:
            content = pattern.sub('[REDACTED]', content)

        return Document(
            page_content=content,
            metadata=document.metadata
        )

    @classmethod
    def get_filter_stats(cls, original_docs: List[Document], filtered_docs: List[Document]) -> Dict[str, int]:
        """Get statistics about document filtering.

        Args:
            original_docs: Original document list
            filtered_docs: Filtered document list

        Returns:
            Statistics dictionary
        """
        return {
            'original_count': len(original_docs),
            'filtered_count': len(filtered_docs),
            'rejected_count': len(original_docs) - len(filtered_docs),
        }