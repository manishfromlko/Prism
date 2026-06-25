"""Text processing utilities for document chunking and splitting."""

import logging
from typing import List, Optional

from langchain_text_splitters import (
    MarkdownTextSplitter,
    PythonCodeTextSplitter,
    RecursiveCharacterTextSplitter,
)

from .config import RetrievalConfig

logger = logging.getLogger(__name__)


class TextProcessor:
    """Processor for splitting text into chunks for embedding."""

    def __init__(self, config: Optional[RetrievalConfig] = None):
        """Initialize the text processor.

        Args:
            config: Retrieval configuration
        """
        self.config = config or RetrievalConfig()

        # Initialize splitters
        self._recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        self._markdown_splitter = MarkdownTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )

        self._python_splitter = PythonCodeTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )

    def split_text(self, text: str, content_type: str = "text") -> List[str]:
        """Split text into chunks based on content type.

        Args:
            text: Input text to split
            content_type: Type of content (notebook, python, markdown, etc.)

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        try:
            if content_type == "notebook":
                # Notebooks often contain mixed content, use recursive splitter
                chunks = self._recursive_splitter.split_text(text)
            elif content_type in ["python", "script"]:
                # Python code splitting
                chunks = self._python_splitter.split_text(text)
            elif content_type == "markdown":
                # Markdown splitting
                chunks = self._markdown_splitter.split_text(text)
            else:
                # Default recursive splitting
                chunks = self._recursive_splitter.split_text(text)

            # Filter out empty chunks
            chunks = [chunk for chunk in chunks if chunk.strip()]

            logger.debug(f"Split text into {len(chunks)} chunks for type {content_type}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to split text: {e}")
            # Fallback to simple splitting
            return self._fallback_split(text)

    def _fallback_split(self, text: str) -> List[str]:
        """Fallback text splitting method.

        Args:
            text: Input text

        Returns:
            List of text chunks
        """
        # Simple character-based splitting
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.config.chunk_size, text_len)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.config.chunk_overlap

        return chunks

    def split_documents(self, documents: List[dict]) -> List[dict]:
        """Split multiple documents into chunks.

        Args:
            documents: List of document dictionaries with 'content' and 'metadata'

        Returns:
            List of chunk dictionaries with updated metadata
        """
        chunked_documents = []

        for doc in documents:
            content = doc.get('content', '')
            content_type = doc.get('metadata', {}).get('type', 'text')

            chunks = self.split_text(content, content_type)

            for i, chunk in enumerate(chunks):
                chunk_doc = {
                    'content': chunk,
                    'metadata': {
                        **doc.get('metadata', {}),
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'original_length': len(content)
                    }
                }
                chunked_documents.append(chunk_doc)

        logger.info(f"Split {len(documents)} documents into {len(chunked_documents)} chunks")
        return chunked_documents

    def estimate_chunks(self, text: str, content_type: str = "text") -> int:
        """Estimate the number of chunks for given text.

        Args:
            text: Input text
            content_type: Content type

        Returns:
            Estimated number of chunks
        """
        if not text:
            return 0

        # Rough estimation based on chunk size
        avg_chars_per_chunk = self.config.chunk_size - self.config.chunk_overlap
        estimated_chunks = max(1, len(text) // avg_chars_per_chunk)

        return estimated_chunks