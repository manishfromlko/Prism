"""Prompt builder functions — load templates from prompts/chatbot/ and fill placeholders."""

from typing import Dict, List

from .prompt_loader import load_prompt


def build_doc_qa_messages(retrieved_chunks: List[Dict], user_query: str) -> List[Dict]:
    chunk_text = "\n\n---\n\n".join(
        f"[{c.get('source_file', 'unknown')}]\n{c.get('chunk_text', '')}"
        for c in retrieved_chunks
    )
    return [
        {"role": "system", "content": load_prompt("chatbot/doc_qa/system.txt")},
        {"role": "user", "content": load_prompt("chatbot/doc_qa/user.txt").format(
            retrieved_chunks=chunk_text or "No documentation found.",
            user_query=user_query,
        )},
    ]


def build_artifact_search_messages(artifact_results: List[Dict], user_query: str) -> List[Dict]:
    artifact_text = "\n\n---\n\n".join(
        f"Artifact: {a.get('artifact_id', 'unknown')}\nOwner: {a.get('user_id', 'unknown')}\n"
        f"Tags: {a.get('tags', '')}\nSummary: {a.get('artifact_summary', '')}"
        for a in artifact_results
    )
    return [
        {"role": "system", "content": load_prompt("chatbot/artifact_search/system.txt")},
        {"role": "user", "content": load_prompt("chatbot/artifact_search/user.txt").format(
            artifact_results=artifact_text or "No artifacts found.",
            user_query=user_query,
        )},
    ]


def build_user_search_messages(user_results: List[Dict], user_query: str) -> List[Dict]:
    user_text = "\n\n---\n\n".join(
        f"User: {u.get('user_id', 'unknown')}\nTags: {u.get('tags', '')}\nProfile: {u.get('user_profile', '')}"
        for u in user_results
    )
    return [
        {"role": "system", "content": load_prompt("chatbot/user_search/system.txt")},
        {"role": "user", "content": load_prompt("chatbot/user_search/user.txt").format(
            user_results=user_text or "No user profiles found.",
            user_query=user_query,
        )},
    ]


def build_hybrid_messages(
    doc_chunks: List[Dict],
    artifact_results: List[Dict],
    user_results: List[Dict],
    user_query: str,
) -> List[Dict]:
    doc_text = "\n\n---\n\n".join(
        f"[{c.get('source_file', 'unknown')}]\n{c.get('chunk_text', '')}" for c in doc_chunks
    )
    artifact_text = "\n\n---\n\n".join(
        f"Artifact: {a.get('artifact_id', 'unknown')}\nOwner: {a.get('user_id', 'unknown')}\n"
        f"Summary: {a.get('artifact_summary', '')}"
        for a in artifact_results
    )
    user_text = "\n\n---\n\n".join(
        f"User: {u.get('user_id', 'unknown')}\nProfile: {u.get('user_profile', '')}"
        for u in user_results
    )
    return [
        {"role": "system", "content": load_prompt("chatbot/hybrid/system.txt")},
        {"role": "user", "content": load_prompt("chatbot/hybrid/user.txt").format(
            doc_chunks=doc_text or "No documentation found.",
            artifact_results=artifact_text or "No artifacts found.",
            user_results=user_text or "No user profiles found.",
            user_query=user_query,
        )},
    ]
