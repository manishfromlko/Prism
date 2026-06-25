"""Lightweight conversational memory helpers for chatbot follow-up turns."""

from __future__ import annotations

import re
from typing import Dict, List, Optional


def normalize_user_id_text(value: str) -> str:
    """Normalize a user-entered ID while preserving digits."""
    return re.sub(r"[^a-z0-9._-]+", "", value.lower().strip())


def extract_recent_user_candidates(history: List[Dict], all_user_ids: List[str]) -> List[str]:
    """Extract candidate user IDs from the latest assistant clarification."""
    known_ids = {uid.lower(): uid for uid in all_user_ids}
    for message in reversed(history):
        if message.get("role") != "assistant":
            continue

        content = message.get("content", "")
        if "Top Matches:" not in content and "Follow-up Question:" not in content:
            continue

        candidates: List[str] = []
        for line in content.splitlines():
            match = re.match(r"\s*(?:[-*•]|\d+[.)])\s*([A-Za-z][\w.-]+)\s*$", line)
            if not match:
                continue
            uid = known_ids.get(match.group(1).lower())
            if uid:
                candidates.append(uid)
        if candidates:
            return candidates
    return []


def extract_recent_profile_user(history: List[Dict], all_user_ids: List[str]) -> Optional[str]:
    """Return the latest profile user shown by the assistant, if any."""
    known_ids = {uid.lower(): uid for uid in all_user_ids}
    for message in reversed(history):
        if message.get("role") != "assistant":
            continue
        content = message.get("content", "")
        match = re.search(r"\*\*([A-Za-z][\w.-]+)\*\*", content)
        if not match:
            continue
        uid = known_ids.get(match.group(1).lower())
        if uid:
            return uid
    return None


def _looks_like_contextual_followup(query: str) -> bool:
    normalized = query.lower()
    return bool(
        re.search(
            r"\b(he|she|they|him|her|them|his|their|that|this|person|profile|"
            r"more|details|notebooks?|projects?|work|working|artifacts?)\b",
            normalized,
        )
    )


def resolve_user_from_context(
    query: str,
    history: List[Dict],
    all_user_ids: List[str],
) -> Optional[str]:
    """Resolve exact user-id selections, especially after a disambiguation turn."""
    normalized_query = normalize_user_id_text(query)
    if not normalized_query:
        return None

    known_ids = {normalize_user_id_text(uid): uid for uid in all_user_ids}
    if normalized_query in known_ids:
        return known_ids[normalized_query]

    recent_candidates = extract_recent_user_candidates(history, all_user_ids)
    for candidate in recent_candidates:
        if normalized_query == normalize_user_id_text(candidate):
            return candidate

    if _looks_like_contextual_followup(query):
        return extract_recent_profile_user(history, all_user_ids)

    return None
