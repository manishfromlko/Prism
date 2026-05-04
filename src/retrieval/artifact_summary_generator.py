"""Generate artifact-level summaries and tags via LiteLLM chat completion."""

import json
import logging
from pathlib import Path
from typing import Dict, List

from .config import make_openai_client

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "artifact_summary_prompt.txt"
MAX_ARTIFACT_CONTENT_CHARS = 5000


def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _extract_text_for_artifact(artifact: Dict) -> str:
    source_path = artifact.get("capture_source", {}).get("source_path", "")
    if not source_path:
        return ""

    try:
        with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:MAX_ARTIFACT_CONTENT_CHARS]
    except Exception:
        return ""


def _call_llm(
    client,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    frequency_penalty: float,
    presence_penalty: float,
) -> Dict:
    logger.info(
        "Artifact summary LLM call params: "
        f"model={model}, temperature={temperature}, max_tokens={max_tokens}, "
        f"top_p={top_p}, frequency_penalty={frequency_penalty}, presence_penalty={presence_penalty}, "
        "response_format=json_object"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict technical analyst. "
                    "Return valid JSON only and follow all constraints exactly."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    return json.loads(raw)


def generate_artifact_summaries(
    catalog_path: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    max_tokens: int = 220,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
) -> List[Dict]:
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    prompt_template = _load_prompt_template()
    client = make_openai_client()
    artifacts = list(catalog.get("artifacts", {}).values())

    summaries: List[Dict] = []
    for artifact in artifacts:
        workspace_id = artifact.get("workspace_id", "")
        artifact_id = artifact.get("artifact_id", "")
        artifact_name = artifact.get("file_name", "")
        artifact_type = artifact.get("file_type", "")
        language = (
            artifact.get("classification", {}).get("metadata", {}).get("language", "")
            or artifact_type
        )

        if not workspace_id or not artifact_id:
            continue
        if artifact_type not in {"notebook", "script", "text"}:
            continue

        content = _extract_text_for_artifact(artifact)
        prompt = (
            prompt_template
            .replace("{workspace_id}", workspace_id)
            .replace("{artifact_id}", artifact_id)
            .replace("{artifact_name}", artifact_name)
            .replace("{artifact_type}", artifact_type)
            .replace("{language}", str(language))
            .replace("{content}", content)
        )

        try:
            parsed = _call_llm(
                client=client,
                model=model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
            )
            summary_text = str(parsed.get("artifact_summary", "")).strip()
            if not summary_text:
                summary_text = "Insufficient context to determine intent."
            summary_text = summary_text[:1200]

            tags_raw = parsed.get("tags", [])
            if not isinstance(tags_raw, list):
                tags_raw = []
            tags = ",".join(
                str(tag).strip().lower() for tag in tags_raw if str(tag).strip()
            )[:1000]

            summaries.append({
                "user_id": workspace_id,
                "artifact_id": artifact_id,
                "artifact_summary": summary_text,
                "tags": tags,
            })
        except Exception as e:
            logger.error(f"Failed to summarize artifact {artifact_id}: {e}")
            continue

    return summaries
