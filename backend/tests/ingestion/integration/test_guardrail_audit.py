import json
from pathlib import Path

from src.ingestion.pipeline import IngestionPipeline


def test_guardrail_skips_sensitive_and_unsupported_files():
    root = Path("/tmp/guard_test")
    if root.exists():
        import shutil
        shutil.rmtree(root)
    workspace_dir = root / "user1"
    workspace_dir.mkdir(parents=True)

    # Create normal files
    notebook_path = workspace_dir / "analysis.ipynb"
    notebook_path.write_text(
        json.dumps(
            {
                "metadata": {"title": "Analysis", "kernelspec": {"language": "python"}},
                "cells": [{"cell_type": "code", "source": ["print(\"hello\")"]}],
            }
        ),
        encoding="utf-8",
    )

    # Create sensitive file
    env_path = workspace_dir / ".env"
    env_path.write_text("SECRET_KEY=123\n", encoding="utf-8")

    # Create unsupported file
    bin_path = workspace_dir / "binary.exe"
    bin_path.write_text("fake binary", encoding="utf-8")

    # Run ingestion
    pipeline = IngestionPipeline(root_path=str(root), mode="full", dry_run=False)
    pipeline.run()

    summary = pipeline.storage.summary()
    assert summary["workspaces"] == 1
    assert summary["artifacts"] == 1  # Only the notebook, others skipped
    assert summary["audit_records"] == 2  # Two skipped

    # Check audit records
    audits = pipeline.storage._audit
    assert len(audits) == 2

    audit_reasons = [audit["reason"] for audit in audits]
    assert "guardrail detected sensitive or unsupported artifact" in audit_reasons

    # Check that skipped files have audit
    env_audit = next((a for a in audits if "user1:.env" in a.get("artifact_id", "")), None)
    assert env_audit is not None
    assert env_audit["decision"] == "skipped"
    assert env_audit["matched_pattern"] == "sensitive"

    bin_audit = next((a for a in audits if "user1:binary.exe" in a.get("artifact_id", "")), None)
    assert bin_audit is not None
    assert bin_audit["decision"] == "skipped"
    assert bin_audit["matched_pattern"] == "unsupported_extension"

    import shutil
    shutil.rmtree(root)
    print("GUARD_TEST_PASSED")