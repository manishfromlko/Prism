"""Integration tests for document processing pipeline."""

import json
import tempfile
from pathlib import Path

import pytest

from src.retrieval.config import RetrievalConfig
from src.retrieval.document_loader import DocumentLoader
from src.retrieval.text_processor import TextProcessor


class TestDocumentProcessing:
    """Integration tests for document processing."""

    def test_full_pipeline_with_sample_catalog(self):
        """Test the complete document processing pipeline."""
        # Create sample catalog data
        catalog_data = {
            "workspaces": {
                "ws1": {
                    "id": "ws1",
                    "name": "Test Workspace",
                    "owner": "testuser",
                    "path": "/test/ws1"
                }
            },
            "artifacts": {
                "art1": {
                    "id": "art1",
                    "workspace_id": "ws1",
                    "type": "notebook",
                    "path": "analysis.ipynb",
                    "size": 1024,
                    "modified_at": "2024-01-01T00:00:00Z",
                    "content": json.dumps({
                        "metadata": {"kernelspec": {"language": "python"}},
                        "cells": [
                            {"cell_type": "code", "source": ["print('hello world')"]},
                            {"cell_type": "markdown", "source": ["# Analysis\n\nThis is a test."]}
                        ]
                    })
                },
                "art2": {
                    "id": "art2",
                    "workspace_id": "ws1",
                    "type": "python",
                    "path": "script.py",
                    "size": 256,
                    "modified_at": "2024-01-01T00:00:00Z",
                    "content": "def hello():\n    print('Hello from script')\n\nhello()"
                }
            }
        }

        # Create temporary catalog file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(catalog_data, f)
            catalog_path = f.name

        try:
            # Initialize components
            config = RetrievalConfig()
            loader = DocumentLoader(catalog_path, config)
            processor = TextProcessor(config)

            # Load documents
            documents = loader.load_documents(apply_guardrails=False)

            assert len(documents) == 2

            # Check notebook document
            notebook_doc = next(d for d in documents if d.metadata['artifact_id'] == 'art1')
            assert notebook_doc.metadata['type'] == 'notebook'
            assert 'hello world' in notebook_doc.page_content
            assert '# Analysis' in notebook_doc.page_content
            assert notebook_doc.metadata['workspace_name'] == 'Test Workspace'

            # Check script document
            script_doc = next(d for d in documents if d.metadata['artifact_id'] == 'art2')
            assert script_doc.metadata['type'] == 'python'
            assert 'def hello():' in script_doc.page_content

            # Test text processing
            chunked = processor.split_documents([
                {'content': notebook_doc.page_content, 'metadata': notebook_doc.metadata},
                {'content': script_doc.page_content, 'metadata': script_doc.metadata}
            ])

            assert len(chunked) >= 2  # At least one chunk per document

        finally:
            Path(catalog_path).unlink()

    def test_text_splitting_strategies(self):
        """Test different text splitting strategies."""
        config = RetrievalConfig(chunk_size=100, chunk_overlap=20)
        processor = TextProcessor(config)

        # Test Python code splitting
        python_code = """
def function_one():
    print("First function")
    return True

def function_two():
    print("Second function")
    return False

class MyClass:
    def method(self):
        pass
"""

        chunks = processor.split_text(python_code, "python")
        assert len(chunks) > 1
        assert any("def function_one" in chunk for chunk in chunks)

        # Test markdown splitting
        markdown_text = """
# Section 1

This is the first section with some content.

## Subsection 1.1

More content here.

# Section 2

This is the second section.
"""

        chunks = processor.split_text(markdown_text, "markdown")
        assert len(chunks) > 1
        assert any("# Section 1" in chunk for chunk in chunks)

        # Test general text splitting
        long_text = "This is a long text. " * 50
        chunks = processor.split_text(long_text, "text")
        assert len(chunks) > 1
        assert all(len(chunk) <= config.chunk_size + config.chunk_overlap for chunk in chunks)

    def test_document_filtering(self):
        """Test document filtering with guardrails."""
        from src.retrieval.document_guard import DocumentGuard
        from langchain_core.documents import Document

        # Create test documents
        safe_doc = Document(
            page_content="This is safe content",
            metadata={"artifact_id": "safe", "type": "notebook"}
        )

        sensitive_doc = Document(
            page_content="My password is secret123",
            metadata={"artifact_id": "sensitive", "type": "notebook"}
        )

        unsupported_doc = Document(
            page_content="Binary content",
            metadata={"artifact_id": "binary", "type": "binary"}
        )

        documents = [safe_doc, sensitive_doc, unsupported_doc]
        filtered = DocumentGuard.filter_documents(documents)

        # Only safe document should remain
        assert len(filtered) == 1
        assert filtered[0].metadata["artifact_id"] == "safe"

    def test_metadata_enrichment(self):
        """Test metadata enrichment with workspace context."""
        catalog_data = {
            "workspaces": {
                "ws1": {
                    "id": "ws1",
                    "name": "Enriched Workspace",
                    "owner": "testowner",
                    "path": "/test/path"
                }
            },
            "artifacts": {
                "art1": {
                    "id": "art1",
                    "workspace_id": "ws1",
                    "type": "notebook",
                    "path": "test.ipynb",
                    "content": json.dumps({"cells": []})
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(catalog_data, f)
            catalog_path = f.name

        try:
            loader = DocumentLoader(catalog_path)
            documents = loader.load_documents(apply_guardrails=False)

            assert len(documents) == 1
            doc = documents[0]

            # Check enriched metadata
            assert doc.metadata['workspace_name'] == 'Enriched Workspace'
            assert doc.metadata['workspace_owner'] == 'testowner'
            assert doc.metadata['artifact_count_in_workspace'] == 1

        finally:
            Path(catalog_path).unlink()