from pathlib import Path

from src.ingestion.guards import classify_file


def test_classify_sensitive_file() -> None:
    path = Path("/tmp/dataset/user1/.env")
    result = classify_file(path)

    assert result["decision"] == "skipped"
    assert result["matched_pattern"] == "sensitive"
    assert result["classification"] == "sensitive"


def test_classify_python_script() -> None:
    path = Path("/tmp/dataset/user1/script.py")
    result = classify_file(path)

    assert result["decision"] == "ingested"
    assert result["classification"] == "processable"
