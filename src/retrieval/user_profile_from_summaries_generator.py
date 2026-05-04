"""Generate user profiles from artifact summaries stored in Milvus.

Unlike user_profile_generator.py (which reads raw source files), this module
pulls pre-generated artifact summaries from the artifact_summaries Milvus
collection and feeds them as context to the LLM.  This produces more concise,
signal-dense profiles because the LLM works from already-distilled summaries
rather than raw code.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .artifact_summary_store import ArtifactSummaryStore
from .config import RetrievalConfig, make_openai_client

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "user_profile_from_summaries_prompt.txt"


def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _call_llm(client, model: str, prompt: str) -> Dict:
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
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    return json.loads(raw)


def _build_summaries_context(summaries: List[Dict]) -> str:
    """Format artifact summaries into a readable context block for the LLM."""
    lines: List[str] = []
    for s in summaries:
        artifact_id = s.get("artifact_id", "unknown")
        summary_text = s.get("artifact_summary", "").strip()
        tags = s.get("tags", "").strip()
        if not summary_text:
            continue
        lines.append(f"- [{artifact_id}] {summary_text}")
        if tags:
            lines.append(f"  Tags: {tags}")
    return "\n".join(lines)


def generate_profiles_from_summaries(
    config: RetrievalConfig,
    model: str = "gpt-4o-mini",
) -> List[Dict]:
    """
    Read artifact summaries from Milvus, call gpt-4o-mini once per user, and
    return profile dicts ready for embedding and upsert.

    Each dict has: id, user_id, user_profile, tags.
    The caller must add 'vector' before passing to UserProfileStore.upsert_profiles().

    Requires the artifact_summaries collection to be populated first.
    Run: python -m src.retrieval.artifact_summary_indexer --mode full
    """
    summary_store = ArtifactSummaryStore(config)
    summary_store.create_collection(drop_if_exists=False)

    all_summaries = summary_store.get_all_summaries()
    if not all_summaries:
        logger.warning(
            "No artifact summaries found in Milvus. "
            "Run `python -m src.retrieval.artifact_summary_indexer --mode full` first."
        )
        return []

    summaries_by_user: Dict[str, List[Dict]] = {}
    for s in all_summaries:
        uid = s.get("user_id", "")
        if uid:
            summaries_by_user.setdefault(uid, []).append(s)

    logger.info(f"Found summaries for {len(summaries_by_user)} users")

    prompt_template = _load_prompt_template()
    client = make_openai_client()
    profiles: List[Dict] = []

    for user_id, summaries in summaries_by_user.items():
        logger.info(f"Generating profile for {user_id} ({len(summaries)} artifact summaries)...")

        context = _build_summaries_context(summaries)
        if not context.strip():
            logger.warning(f"  No usable summaries for {user_id} — skipping")
            continue

        prompt = (
            prompt_template
            .replace("{user_id}", user_id)
            .replace("{summaries}", context)
        )

        try:
            parsed = _call_llm(client, model, prompt)

            profile_text = str(parsed.get("profile", "")).strip()[:450]
            tags_raw = parsed.get("tags", [])
            if not isinstance(tags_raw, list):
                tags_raw = []
            tags = ",".join(str(t).strip() for t in tags_raw if t)[:1000]

            profiles.append({
                "user_id": user_id,
                "user_profile": profile_text,
                "tags": tags,
            })

            logger.info(f"  Profile ({len(profile_text)} chars): {profile_text[:100]}...")
            logger.info(f"  Tags: {tags}")

        except Exception as e:
            logger.error(f"  LLM call failed for {user_id}: {e}")
            continue

    return profiles
