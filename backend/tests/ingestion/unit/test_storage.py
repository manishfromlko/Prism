from pathlib import Path

from src.ingestion.models import FileArtifact, FileType, IngestionAudit, Workspace
from src.ingestion.storage import Storage


def test_storage_write_and_load(tmp_path: Path) -> None:
    base_path = tmp_path / "ingestion"
    storage = Storage(base_path)

    workspace = Workspace(
        workspace_id="user1",
        owner="user1",
        root_path="/tmp/dataset/user1",
        file_count=1,
    )
    storage.write_workspace(workspace)

    artifact = FileArtifact(
        artifact_id="user1:script.py",
        workspace_id="user1",
        relative_path="script.py",
        file_name="script.py",
        file_type=FileType.SCRIPT,
        size_bytes=100,
    )
    storage.write_artifact(artifact)

    audit = IngestionAudit(
        audit_id="audit_1",
        artifact_id=artifact.artifact_id,
        workspace_id="user1",
        run_id="run_1",
        decision="ingested",
        reason="test",
    )
    storage.write_audit(audit)
    storage.save()

    loaded_storage = Storage(base_path)
    assert loaded_storage.get_workspace("user1")["file_count"] == 1
    assert loaded_storage.get_artifact("user1:script.py")["file_name"] == "script.py"
    assert len(loaded_storage._audit) == 1
