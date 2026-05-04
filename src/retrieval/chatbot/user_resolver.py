"""
User name resolver — three-stage pipeline:

  1. String retrieval  — normalize UIDs (strip digits/dots) + token filter +
                         RapidFuzz scoring against all user_ids
                         (no vector search, no LLM, deterministic)
  2. Exact match       — single high-confidence hit → return uid, caller fetches
                         raw profile (zero LLM calls on this path)
  3. Disambiguation    — multiple/ambiguous hits → LLM name-resolution prompt
                         with top-5 candidates as context
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from ...observability import litellm_metadata
from ..config import make_openai_client
from ..user_profile_store import UserProfileStore
from .prompt_loader import load_prompt

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "who", "is", "are", "was", "what", "does", "do", "did", "work", "working",
    "worked", "on", "tell", "me", "about", "find", "show", "get", "fetch",
    "the", "a", "an", "i", "can", "you", "for", "with", "in", "at", "to",
    "of", "and", "how", "where", "when", "which", "profile", "person",
    "user", "workspace", "currently", "now", "details", "info",
}

_MIN_FUZZY_SCORE = 60   # discard candidates below this (0–100 scale)
_EXACT_THRESHOLD = 90   # single candidate treated as an unambiguous match


# ---------------------------------------------------------------------------
# Normalisation + scoring helpers (pure functions, no I/O)
# ---------------------------------------------------------------------------

def _extract_name_tokens(query: str) -> List[str]:
    """Pull candidate name tokens out of a natural-language query."""
    raw = re.split(r"\W+", query.lower())
    return [t for t in raw if t and len(t) > 1 and t not in _STOP_WORDS]


def _normalize_uid(uid: str) -> str:
    """
    Convert a username to a plain 'first last' string.
      ravi.verma      → 'ravi verma'
      dhruv2.aggarwal → 'dhruv aggarwal'
      amit23.sharma   → 'amit sharma'
    """
    clean = re.sub(r"\d+", "", uid.lower())      # strip embedded digits
    clean = re.sub(r"[._]+", " ", clean)          # dots/underscores → space
    return clean.strip()


def _score_uid(uid: str, query_name: str, name_tokens: List[str]) -> float:
    """
    Return a relevance score in [0, 100].

    Steps:
      (B) Token filter — at least one query token must be a substring of (or
          prefix-matched against) the first or last name component.  Candidates
          that fail this filter get 0.0 without fuzzy evaluation.
      (C) RapidFuzz token_set_ratio — handles reordering, partial overlap.
    """
    normalized = _normalize_uid(uid)
    parts = normalized.split()
    first = parts[0] if parts else ""
    last = parts[1] if len(parts) > 1 else ""

    token_match = any(
        t in first or t in last or first.startswith(t) or last.startswith(t)
        for t in name_tokens
    )
    if not token_match:
        return 0.0

    return float(fuzz.token_set_ratio(query_name, normalized))


def retrieve_candidates(
    query: str,
    all_user_ids: List[str],
    top_k: int = 5,
    min_score: float = _MIN_FUZZY_SCORE,
) -> List[Tuple[str, float]]:
    """
    Local name match: return up to top_k (uid, score) pairs sorted by score desc.
    Scores are in [0, 100]; candidates below min_score are discarded.
    """
    name_tokens = _extract_name_tokens(query)
    if not name_tokens:
        return []

    query_name = " ".join(name_tokens)
    scored = [(uid, _score_uid(uid, query_name, name_tokens)) for uid in all_user_ids]
    filtered = [(uid, s) for uid, s in scored if s >= min_score]
    filtered.sort(key=lambda x: -x[1])
    return filtered[:top_k]


# ---------------------------------------------------------------------------
# Resolver class
# ---------------------------------------------------------------------------

class UserNameResolver:
    """
    Resolves a partial name query to either:
      - an unambiguous exact_uid (caller fetches raw profile, no LLM)
      - an LLM-generated disambiguation message (top-5 candidates as context)
    """

    def __init__(self, user_store: UserProfileStore, model: str = "gpt-4o-mini"):
        self.client = make_openai_client()
        self.model = model
        self.user_store = user_store
        self._system_prompt = load_prompt("chatbot/user_resolution/system.txt")
        self._user_template = load_prompt("chatbot/user_resolution/user.txt")

    def resolve(
        self,
        query: str,
        candidates: Optional[List[Tuple[str, float]]] = None,
        trace_id: Optional[str] = None,
    ) -> Dict:
        """
        Returns one of:
          {"exact_uid": "<user_id>", "answer": None}
              → single unambiguous match; caller fetches the profile (no LLM)
          {"exact_uid": None, "answer": "<text>"}
              → LLM disambiguation message to show the user
        """
        if candidates is None:
            all_ids = self.user_store.get_all_user_ids()
            candidates = retrieve_candidates(query, all_ids)

        # ── Stage 1: no string match ──────────────────────────────────────────
        if not candidates:
            return {
                "exact_uid": None,
                "answer": (
                    "I couldn't find any users matching that name. "
                    "Please check the spelling and try again."
                ),
            }

        # ── Stage 2: unambiguous match — no LLM needed ───────────────────────
        # Either a single candidate above threshold, or top score is perfect
        # (100) with a clear gap (≥ 20 points) over the second-best candidate.
        top_uid, top_score = candidates[0]
        next_score = candidates[1][1] if len(candidates) > 1 else 0.0
        unambiguous = (
            (len(candidates) == 1 and top_score >= _EXACT_THRESHOLD)
            or (top_score == 100.0 and next_score < 85.0)
        )
        if unambiguous:
            logger.info(
                f"Exact name match: '{top_uid}' (score={top_score:.0f}, next={next_score:.0f})"
            )
            return {"exact_uid": top_uid, "answer": None}

        # ── Stage 3: ambiguous — LLM disambiguation with top-5 as context ────
        top_names = "\n".join(f"- {uid}" for uid, _ in candidates)
        user_message = self._user_template.format(
            user_query=query,
            available_names=top_names,
        )
        logger.info(
            f"Ambiguous name query '{query}' — "
            f"passing {len(candidates)} candidates to LLM"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,
                max_tokens=250,
                extra_body=litellm_metadata(trace_id, "name_resolve") if trace_id else None,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"UserNameResolver LLM call failed: {e}")
            answer = (
                "I found several users that might match — could you provide "
                "the last name or more context?\n\n"
                + "\n".join(f"• {uid}" for uid, _ in candidates)
            )

        return {"exact_uid": None, "answer": answer}
