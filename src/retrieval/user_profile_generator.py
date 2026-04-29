"""Generate user profiles via OpenAI chat completion from real workspace content."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "user_profile_prompt.txt"

# Per-artifact content budget and total context cap
MAX_CHARS_PER_NOTEBOOK = 500
MAX_CHARS_PER_SCRIPT = 400
MAX_CONTEXT_CHARS = 24_000

# Data-access patterns to surface for the LLM
DATA_ACCESS_KEYWORDS = (
    "spark.read", "spark.sql", "spark.table", "sc.textFile",
    "hdfs://", "s3://", "s3a://", "s3n://",
    "FROM ", "JOIN ", "SELECT ", ".table(", ".parquet(",
    ".csv(", ".json(", ".orc(", ".delta(", "kafka", "topic",
    "sqlContext", "read_csv", "read_parquet", "read_table",
    "createOrReplaceTempView", "registerTempTable",
)


# ---------------------------------------------------------------------------
# Content extraction helpers
# ---------------------------------------------------------------------------

def _extract_notebook_context(path: str) -> str:
    """Extract markdown headers + import lines + data-access lines from a notebook."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            nb = json.load(f)
    except Exception:
        return ""

    headers: List[str] = []
    imports: List[str] = []
    data_lines: List[str] = []

    for cell in nb.get("cells", []):
        cell_type = cell.get("cell_type", "")
        source = "".join(cell.get("source", []))

        if cell_type == "markdown":
            for line in source.splitlines():
                if line.startswith("#"):
                    headers.append(line.strip())
                    if len(headers) >= 4:
                        break

        elif cell_type == "code":
            for line in source.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if stripped.startswith(("import ", "from ")):
                    imports.append(stripped)
                elif any(kw in line for kw in DATA_ACCESS_KEYWORDS):
                    data_lines.append(stripped)

    # Deduplicate while preserving order
    def dedup(lst: List[str]) -> List[str]:
        seen: set = set()
        out: List[str] = []
        for x in lst:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    parts = (
        dedup(headers)[:4]
        + dedup(imports)[:8]
        + dedup(data_lines)[:10]
    )
    return "\n".join(parts)


def _extract_script_context(path: str) -> str:
    """Extract imports + data-access lines from a script."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return ""

    imports: List[str] = []
    data_lines: List[str] = []
    header = [l.rstrip() for l in lines[:15]]  # file-level comments / shebang

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(("import ", "from ")):
            imports.append(stripped)
        elif any(kw in line for kw in DATA_ACCESS_KEYWORDS):
            data_lines.append(stripped)

    def dedup(lst: List[str]) -> List[str]:
        seen: set = set()
        out: List[str] = []
        for x in lst:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    parts = header + dedup(imports)[:8] + dedup(data_lines)[:10]
    return "\n".join(parts)


def _artifact_snippet(artifact: Dict) -> str:
    """Return a labelled text snippet for one artifact, or '' if unreadable."""
    source_path = artifact.get("capture_source", {}).get("source_path", "")
    file_type = artifact.get("file_type", "")
    file_name = artifact.get("file_name", "")

    if not source_path or not os.path.exists(source_path):
        return ""

    if file_type == "notebook":
        content = _extract_notebook_context(source_path)
        budget = MAX_CHARS_PER_NOTEBOOK
    else:
        content = _extract_script_context(source_path)
        budget = MAX_CHARS_PER_SCRIPT

    content = content.strip()
    if not content:
        return ""

    return f"### {file_type.upper()}: {file_name}\n{content[:budget]}\n\n"


def _build_context(artifacts: List[Dict]) -> str:
    """Assemble context string from all artifacts, capped at MAX_CONTEXT_CHARS."""
    parts: List[str] = []
    total = 0
    for art in artifacts:
        snippet = _artifact_snippet(art)
        if snippet:
            if total + len(snippet) > MAX_CONTEXT_CHARS:
                break
            parts.append(snippet)
            total += len(snippet)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Profile generation
# ---------------------------------------------------------------------------

def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _call_llm(client: OpenAI, model: str, prompt: str) -> Optional[Dict]:
    """Call OpenAI chat completion and return parsed JSON, or None on failure."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise technical analyst. "
                    "Always respond with valid JSON only — no markdown, no explanation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


def generate_profiles(
    catalog_path: str,
    openai_api_key: str,
    model: str = "gpt-4o-mini",
) -> List[Dict]:
    """
    Read catalog, call the LLM once per workspace, and return profile dicts.

    Each dict has: id, user_id, user_profile, tech_tags, data_tags.
    The caller adds 'vector' before indexing into Milvus.
    """
    with open(catalog_path) as f:
        catalog = json.load(f)

    artifacts_by_ws: Dict[str, List[Dict]] = {}
    for art in catalog.get("artifacts", {}).values():
        ws = art.get("workspace_id", "")
        if ws:
            artifacts_by_ws.setdefault(ws, []).append(art)

    prompt_template = _load_prompt_template()
    client = OpenAI(api_key=openai_api_key)

    profiles: List[Dict] = []
    for user_id, artifacts in artifacts_by_ws.items():
        logger.info(f"Processing {user_id} ({len(artifacts)} artifacts)...")

        context = _build_context(artifacts)
        if not context.strip():
            logger.warning(f"  No readable content for {user_id} — skipping")
            continue

        logger.info(f"  Context: {len(context):,} chars → calling {model}")
        prompt = (
            prompt_template
            .replace("{user_id}", user_id)
            .replace("{content}", context)
        )

        try:
            parsed = _call_llm(client, model, prompt)

            profile_text = str(parsed.get("profile", "")).strip()[:500]
            tech_tags_raw = parsed.get("tech_tags", [])
            data_tags_raw = parsed.get("data_tags", [])

            # Sanitise: ensure lists of strings
            tech_tags = ",".join(str(t).strip() for t in tech_tags_raw if t)[:500]
            data_tags = ",".join(str(t).strip() for t in data_tags_raw if t)[:500]

            profiles.append({
                "user_id": user_id,
                "user_profile": profile_text,
                "tags": ",".join(filter(None, [tech_tags, data_tags]))[:1000],
            })

            logger.info(f"  profile ({len(profile_text)} chars): {profile_text[:80]}...")
            logger.info(f"  tech_tags: {tech_tags}")
            logger.info(f"  data_tags: {data_tags}")

        except Exception as e:
            logger.error(f"  LLM call failed for {user_id}: {e}")
            continue

    return profiles
