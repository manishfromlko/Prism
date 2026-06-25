import json
from pathlib import Path

from src.ingestion.cli import build_parser
from src.ingestion.pipeline import IngestionPipeline


def test_cli_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["--root", "dataset/", "--mode", "full"])

    assert args.root == "dataset/"
    assert args.mode == "full"
    assert args.dry_run is False


def test_full_ingestion_pipeline_stores_workspace_and_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    workspace_dir = root / "user1"
    workspace_dir.mkdir(parents=True)

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

    script_path = workspace_dir / "extract.py"
    script_path.write_text("import pandas as pd\n", encoding="utf-8")

    pipeline = IngestionPipeline(root_path=str(root), mode="full", dry_run=True)
    pipeline.run()

    summary = pipeline.storage.summary()
    assert summary["workspaces"] == 1
    assert summary["artifacts"] == 2

    workspace = pipeline.storage.get_workspace("user1")
    assert workspace is not None
    assert workspace["file_count"] == 2

    notebook_artifact = pipeline.storage.get_artifact("user1:analysis.ipynb")
    assert notebook_artifact["file_name"] == "analysis.ipynb"
    assert notebook_artifact["classification"]["category"] == "processable"
    assert notebook_artifact["ingestion_status"] == "new"
