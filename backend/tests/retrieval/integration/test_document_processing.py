"""Integration tests for document processing pipeline."""

import json

from src.retrieval.document_loader import DocumentLoader
from src.retrieval.config import RetrievalConfig
from src.retrieval.text_processor import TextProcessor


class FakeMetadataRepository:
    enabled = True

    def __init__(self, workspaces, artifacts):
        self.workspaces = workspaces
        self.artifacts = artifacts

    def list_workspaces(self):
        return self.workspaces

    def list_artifacts(self, workspace_id=None):
        if workspace_id:
            return [a for a in self.artifacts if a.get("workspace_id") == workspace_id]
        return self.artifacts

    def artifact_counts_by_workspace(self):
        counts = {}
        for artifact in self.artifacts:
            workspace_id = artifact.get("workspace_id", "")
            counts[workspace_id] = counts.get(workspace_id, 0) + 1
        return counts


class TestDocumentProcessing:
    """Integration tests for document processing."""

    def test_full_pipeline_with_sample_metadata(self):
        """Test the complete document processing pipeline."""
        workspaces = [
            {
                "workspace_id": "ws1",
                "owner": "testuser",
                "root_path": "/test/ws1",
            }
        ]
        artifacts = [
            {
                "artifact_id": "art1",
                "workspace_id": "ws1",
                "file_type": "notebook",
                "relative_path": "analysis.ipynb",
                "size_bytes": 1024,
                "last_modified_at": "2024-01-01T00:00:00Z",
                "content": json.dumps({
                    "metadata": {"kernelspec": {"language": "python"}},
                    "cells": [
                        {"cell_type": "code", "source": ["print('hello world')"]},
                        {"cell_type": "markdown", "source": ["# Analysis\n\nThis is a test."]},
                    ],
                }),
                "capture_source": {},
            },
            {
                "artifact_id": "art2",
                "workspace_id": "ws1",
                "file_type": "script",
                "relative_path": "script.py",
                "size_bytes": 256,
                "last_modified_at": "2024-01-01T00:00:00Z",
                "content": "def hello():\n    print('Hello from script')\n\nhello()",
                "capture_source": {},
            },
        ]
        config = RetrievalConfig()
        loader = DocumentLoader(
            config=config,
            metadata_repository=FakeMetadataRepository(workspaces, artifacts),
        )
        processor = TextProcessor(config)

        documents = loader.load_documents(apply_guardrails=False)

        assert len(documents) == 2

        notebook_doc = next(d for d in documents if d.metadata["artifact_id"] == "art1")
        assert notebook_doc.metadata["type"] == "notebook"
        assert "hello world" in notebook_doc.page_content
        assert "# Analysis" in notebook_doc.page_content
        assert notebook_doc.metadata["workspace_name"] == "ws1"

        script_doc = next(d for d in documents if d.metadata["artifact_id"] == "art2")
        assert script_doc.metadata["type"] == "script"
        assert "def hello():" in script_doc.page_content

        chunked = processor.split_documents([
            {"content": notebook_doc.page_content, "metadata": notebook_doc.metadata},
            {"content": script_doc.page_content, "metadata": script_doc.metadata},
        ])

        assert len(chunked) >= 2

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
            page_content="password=secret123",
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
        loader = DocumentLoader(
            metadata_repository=FakeMetadataRepository(
                workspaces=[
                    {
                        "workspace_id": "ws1",
                        "owner": "testowner",
                        "root_path": "/test/path",
                    }
                ],
                artifacts=[
                    {
                        "artifact_id": "art1",
                        "workspace_id": "ws1",
                        "file_type": "notebook",
                        "relative_path": "test.ipynb",
                        "content": json.dumps({"cells": [{"cell_type": "markdown", "source": ["hello"]}]}),
                        "capture_source": {},
                    }
                ],
            )
        )
        documents = loader.load_documents(apply_guardrails=False)

        assert len(documents) == 1
        doc = documents[0]

        assert doc.metadata["workspace_name"] == "ws1"
        assert doc.metadata["workspace_owner"] == "testowner"
        assert doc.metadata["artifact_count_in_workspace"] == 1
