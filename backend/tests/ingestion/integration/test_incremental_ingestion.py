import json
from pathlib import Path

from src.ingestion.pipeline import IngestionPipeline


def test_incremental_ingestion_updates_only_changed_files(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    workspace_dir = root / "user1"
    workspace_dir.mkdir(parents=True)

    # Create initial files
    notebook_path = workspace_dir / "analysis.ipynb"
    notebook_content = json.dumps(
        {
            "metadata": {"title": "Analysis", "kernelspec": {"language": "python"}},
            "cells": [{"cell_type": "code", "source": ["print(\"hello\")"]}],
        }
    )
    notebook_path.write_text(notebook_content, encoding="utf-8")

    script_path = workspace_dir / "extract.py"
    script_content = "import pandas as pd\n"
    script_path.write_text(script_content, encoding="utf-8")

    # Run full ingestion
    pipeline = IngestionPipeline(root_path=str(root), mode="full", dry_run=False)
    pipeline.run()

    summary_full = pipeline.storage.summary()
    assert summary_full["workspaces"] == 1
    assert summary_full["artifacts"] == 2

    # Modify one file
    script_path.write_text("import pandas as pd\nimport numpy as np\n", encoding="utf-8")

    # Run incremental ingestion
    pipeline_inc = IngestionPipeline(root_path=str(root), mode="incremental", dry_run=False)
    pipeline_inc.run()

    summary_inc = pipeline_inc.storage.summary()
    assert summary_inc["workspaces"] == 1
    # Should still have 2 artifacts, but one updated
    assert summary_inc["artifacts"] == 2

    # Check statuses
    artifact_script = pipeline_inc.storage.get_artifact("user1:extract.py")
    assert artifact_script["ingestion_status"] == "updated"

    artifact_notebook = pipeline_inc.storage.get_artifact("user1:analysis.ipynb")
    assert artifact_notebook["ingestion_status"] == "unchanged"