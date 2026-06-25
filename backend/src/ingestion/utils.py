import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def normalize_workspace_id(workspace_name: str) -> str:
    return workspace_name.strip().lower()


def compute_file_hash(path: Path) -> Optional[str]:
    try:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, IOError):
        return None


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def safe_list_dir(path: Path) -> List[Path]:
    try:
        return [child for child in path.iterdir()]
    except OSError:
        return []
