"""Structured response formatter — enforces the output schema."""

from typing import Dict, List


def format_response(
    answer: str,
    intent: str,
    confidence: float,
    raw_artifacts: List[Dict] = None,
    raw_users: List[Dict] = None,
    raw_docs: List[Dict] = None,
    exact_match: bool = False,
) -> Dict:
    """
    Build the canonical output schema:
    {answer, intent, confidence, exact_match, artifacts, users, sources}
    """
    raw_artifacts = raw_artifacts or []
    raw_users = raw_users or []
    raw_docs = raw_docs or []

    artifacts = []
    users = []

    if intent in ("ARTIFACT_SEARCH", "HYBRID"):
        for a in raw_artifacts:
            artifacts.append({
                "title": a.get("artifact_id", "unknown"),
                "reason": "Retrieved as relevant artifact",
                "owner": a.get("user_id", "unknown"),
            })

    if intent in ("USER_SEARCH", "HYBRID"):
        for u in raw_users:
            tags = [t.strip() for t in u.get("tags", "").split(",") if t.strip()]
            users.append({
                "name": u.get("user_id", "unknown"),
                "reason": "Retrieved as relevant user",
                "skills": tags,
            })

    sources = []
    if intent in ("DOC_QA", "HYBRID"):
        seen = set()
        for d in raw_docs:
            sf = d.get("source_file", "")
            if sf and sf not in seen:
                seen.add(sf)
                sources.append({"file": sf, "doc_id": d.get("doc_id", "")})

    return {
        "answer": answer.strip(),
        "intent": intent,
        "confidence": round(confidence, 3),
        "exact_match": exact_match,
        "artifacts": artifacts,
        "users": users,
        "sources": sources,
    }
