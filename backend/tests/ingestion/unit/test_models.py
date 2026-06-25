from datetime import datetime

from src.ingestion.models import FileArtifact, FileType, IngestionStatus, Workspace


def test_workspace_model_defaults() -> None:
    workspace = Workspace(
        workspace_id="user1",
        owner="user1",
        root_path="/tmp/dataset/user1",
    )

    assert workspace.workspace_id == "user1"
    assert workspace.file_count == 0
    assert workspace.status == "pending"
    assert workspace.source_coverage == {}


def test_artifact_status_enum() -> None:
    artifact = FileArtifact(
        artifact_id="user1:script.py",
        workspace_id="user1",
        relative_path="script.py",
        file_name="script.py",
        file_type=FileType.SCRIPT,
        size_bytes=100,
        ingestion_status=IngestionStatus.NEW,
    )

    assert artifact.ingestion_status == IngestionStatus.NEW
    assert str(artifact.ingestion_status) == "new"
