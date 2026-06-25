from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional


def extract_metadata_from_notebook(path: Path) -> Dict[str, Optional[str]]:
    try:
        content = path.read_text(encoding="utf-8")
        notebook = json.loads(content)
    except (OSError, ValueError):
        return {}

    metadata: Dict[str, Optional[str]] = {
        "notebook_title": None,
        "kernel_language": None,
        "cells_count": None,
        "extracted_tools": [],
        "database_targets": [],
        "table_references": [],
    }

    metadata["notebook_title"] = notebook.get("metadata", {}).get("title")
    kernelspec = notebook.get("metadata", {}).get("kernelspec", {})
    metadata["kernel_language"] = kernelspec.get("language")
    cells = notebook.get("cells", [])
    metadata["cells_count"] = len(cells)

    raw_text = "\n".join(
        cell.get("source", "") if isinstance(cell.get("source"), str) else "".join(cell.get("source", []))
        for cell in cells
    )

    metadata["extracted_tools"] = _extract_tools(raw_text)
    metadata["database_targets"] = _extract_database_targets(raw_text)
    metadata["table_references"] = _extract_table_references(raw_text)

    return metadata


def extract_metadata_from_script(path: Path) -> Dict[str, Optional[str]]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    return {
        "notebook_title": path.stem,
        "kernel_language": path.suffix.lstrip("."),
        "cells_count": None,
        "extracted_tools": _extract_tools(raw_text),
        "database_targets": _extract_database_targets(raw_text),
        "table_references": _extract_table_references(raw_text),
    }


def _extract_tools(raw_text: str) -> List[str]:
    tools = set()
    tool_patterns = [
        r"\b(pyspark|spark|kafka|postgres|redis|sqlalchemy|pandas|numpy|sklearn)\b",
        r"\b(litellm|langchain|langfuse)\b",
    ]
    for pattern in tool_patterns:
        for match in re.finditer(pattern, raw_text, re.IGNORECASE):
            tools.add(match.group(1).lower())
    return sorted(tools)


def _extract_database_targets(raw_text: str) -> List[str]:
    targets = set()
    for pattern in [r"\b(postgres|mysql|redshift|snowflake|bigquery|oracle|mongo|redis)\b"]:
        for match in re.finditer(pattern, raw_text, re.IGNORECASE):
            targets.add(match.group(1).lower())
    return sorted(targets)


def _extract_table_references(raw_text: str) -> List[str]:
    tables = set()
    patterns = [
        r"\bfrom\s+([\w\.]+)\b",
        r"\bjoin\s+([\w\.]+)\b",
        r"\binto\s+([\w\.]+)\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, raw_text, re.IGNORECASE):
            tables.add(match.group(1))
    return sorted(tables)
