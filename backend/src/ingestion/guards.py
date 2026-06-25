from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional


SENSITIVE_PATTERNS = [
    re.compile(r"\.env", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"credentials?", re.IGNORECASE),
]

UNSUPPORTED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".bin",
    ".so",
    ".class",
    ".pyc",
    ".db",
}


def classify_file(path: Path) -> Dict[str, Optional[str]]:
    metadata: Dict[str, Optional[str]] = {
        "decision": "ingested",
        "matched_pattern": None,
        "classification": "processable",
    }
    name = path.name.lower()
    suffix = path.suffix.lower()

    if any(pattern.search(name) for pattern in SENSITIVE_PATTERNS):
        metadata["decision"] = "skipped"
        metadata["matched_pattern"] = "sensitive"
        metadata["classification"] = "sensitive"
        return metadata

    if suffix in UNSUPPORTED_EXTENSIONS:
        metadata["decision"] = "skipped"
        metadata["matched_pattern"] = "unsupported_extension"
        metadata["classification"] = "unsupported"
        return metadata

    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".mp4", ".mov"}:
        metadata["classification"] = "image"
        return metadata

    if suffix in {".zip", ".tar", ".gz", ".7z"}:
        metadata["classification"] = "archive"
        return metadata

    if suffix in {".py", ".ipynb", ".scala", ".sql", ".txt", ".csv", ".tsv"}:
        metadata["classification"] = "processable"
        return metadata

    metadata["classification"] = "binary"
    return metadata
