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


def is_broad_people_search(query: str) -> bool:
    """Return True for expertise/people searches that should not reuse last user."""
    normalized = query.lower()
    has_group_subject = bool(
        re.search(r"\b(people|users|experts|colleagues|members|team members|who)\b", normalized)
    )
    has_expertise_action = bool(
        re.search(r"\b(work|working|expert|expertise|skills?|know|knows|experience)\b", normalized)
    )
    return has_group_subject and has_expertise_action


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

    if is_broad_people_search(query):
        return None

    recent_candidates = extract_recent_user_candidates(history, all_user_ids)
    for candidate in recent_candidates:
        if normalized_query == normalize_user_id_text(candidate):
            return candidate

    if _looks_like_contextual_followup(query):
        return extract_recent_profile_user(history, all_user_ids)

    return None


def is_greeting(query: str) -> bool:
    """Return True for simple conversational greetings."""
    normalized = re.sub(r"[^a-z\s]+", " ", query.lower()).strip()
    return normalized in {
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "good morning",
        "good afternoon",
        "good evening",
    }


def is_conversation_memory_query(query: str) -> bool:
    """Return True when the user is asking about the current chat history."""
    normalized = query.lower().strip()
    patterns = [
        r"\bwhat (questions|queries|things) (have )?i asked\b",
        r"\bwhat did i ask\b",
        r"\bwhat have i asked\b",
        r"\bquestions i asked\b",
        r"\bwhat did we (talk|discuss) about\b",
        r"\bsummar(y|ize) (our|this) (chat|conversation)\b",
        r"\brecap (our|this) (chat|conversation)\b",
        r"\brepeat (your )?(last|previous) (answer|response)\b",
        r"\bwhat was (your )?(last|previous) (answer|response)\b",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def is_self_intro_query(query: str) -> bool:
    """Return True when the user asks what this assistant is or can do."""
    normalized = query.lower().strip()
    patterns = [
        r"\btell me about yourself\b",
        r"\bwho are you\b",
        r"\bwhat are you\b",
        r"\bwhat can you do\b",
        r"\bwhat do you do\b",
        r"\bintroduce yourself\b",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def is_system_stats_query(query: str) -> bool:
    """Return True for direct questions about indexed system metadata counts."""
    normalized = query.lower().strip()
    patterns = [
        r"\bhow many workspaces\b",
        r"\bnumber of workspaces\b",
        r"\bworkspace count\b",
        r"\bhow many artifacts\b",
        r"\bnumber of artifacts\b",
        r"\bartifact count\b",
        r"\bhow many notebooks\b",
        r"\bhow many scripts\b",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def self_intro_answer() -> str:
    return (
        "I am your workspace intelligence assistant. I can help you search platform "
        "docs, discover notebooks and code artifacts, find people by expertise, "
        "summarize workspace profiles, and recall saved conversation history."
    )


def greeting_answer() -> str:
    return (
        "Hi! I can help with platform docs, artifact discovery, "
        "and finding people or expertise. What would you like to explore?"
    )


def _user_messages(history: List[Dict[str, str]]) -> List[str]:
    return [
        str(message.get("content", "")).strip()
        for message in history
        if message.get("role") == "user" and str(message.get("content", "")).strip()
    ]


def _assistant_messages(history: List[Dict[str, str]]) -> List[str]:
    return [
        str(message.get("content", "")).strip()
        for message in history
        if message.get("role") == "assistant" and str(message.get("content", "")).strip()
    ]


def answer_conversation_memory_query(query: str, history: List[Dict[str, str]]) -> str:
    """Answer chat-history questions directly from the provided conversation."""
    normalized = query.lower()
    assistant_messages = _assistant_messages(history)

    if re.search(r"\b(repeat|last|previous).*(answer|response)\b", normalized):
        if assistant_messages:
            return f"My previous answer was:\n\n{assistant_messages[-1]}"
        return "I do not have a previous answer in this conversation yet."

    asked_questions = _user_messages(history)

    if not asked_questions:
        return "You have not asked any earlier questions in this conversation yet."

    lines = [
        "Before this question, you asked:",
        *[f"{index}. {question}" for index, question in enumerate(asked_questions, start=1)],
    ]

    substantive = [
        question
        for question in asked_questions
        if not is_greeting(question) and not is_conversation_memory_query(question)
    ]
    if substantive:
        lines.append("")
        lines.append(f"The main substantive question was about: {substantive[-1]}")

    return "\n".join(lines)
