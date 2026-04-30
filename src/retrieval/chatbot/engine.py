"""
Chatbot engine — orchestrates: classify → rewrite → retrieve → generate → format.

classify  →  IntentClassifier
rewrite   →  QueryRewriter
retrieve  →  DocRetriever | ArtifactRetriever | UserRetriever (or all for HYBRID)
generate  →  OpenAI chat completion with per-intent prompt template
format    →  formatter.format_response
"""

import logging
import os
from typing import Dict, List, Optional

from openai import OpenAI

from ..artifact_summary_store import ArtifactSummaryStore
from ..config import RetrievalConfig
from ..embeddings import EmbeddingService
from ..user_profile_store import UserProfileStore
from .classifier import IntentClassifier
from .doc_store import DocumentChunkStore
from .formatter import format_response
from .prompts import (
    build_artifact_search_messages,
    build_doc_qa_messages,
    build_hybrid_messages,
    build_user_search_messages,
)
from .query_rewriter import QueryRewriter
from .retrievers import ArtifactRetriever, DocRetriever, UserRetriever

logger = logging.getLogger(__name__)

_OUT_OF_SCOPE_REPLY = (
    "That's outside what I can help with — I don't have access to real-time or external information.\n\n"
    "I'm designed to assist with:\n"
    "• **Platform docs** — how-to guides, onboarding, concepts\n"
    "• **Artifact discovery** — finding notebooks, scripts, and code examples\n"
    "• **People search** — finding colleagues by expertise or what they're working on\n\n"
    "Try asking something like: *\"How do I submit a Spark job?\"* or *\"Who works on NLP?\"*"
)


def _find_exact_user_hit(query: str, user_hits: List[Dict]) -> Optional[Dict]:
    """Return the hit whose user_id appears verbatim in the query, or None."""
    query_lower = query.lower()
    for hit in user_hits:
        user_id = hit.get("user_id", "")
        if user_id and user_id.lower() in query_lower:
            return hit
    return None


def _needs_user_clarification(query: str, user_hits: List[Dict]) -> bool:
    """
    Return True when the query references a person by partial name only
    (i.e. no exact user_id from the results appears verbatim in the query).

    This triggers a disambiguation step instead of a direct answer.
    """
    if not user_hits:
        return False
    query_lower = query.lower()
    for hit in user_hits:
        user_id = hit.get("user_id", "")
        if user_id and user_id.lower() in query_lower:
            return False  # exact user_id found in the query — no ambiguity
    return True


def _build_clarification_response(user_hits: List[Dict], query: str) -> Dict:
    """Return a clarification message listing matched users for the user to confirm."""
    lines = ["I found the following users that might match your query. Could you confirm which one you meant?\n"]
    for hit in user_hits[:5]:
        user_id = hit.get("user_id", "unknown")
        tags = [t.strip() for t in hit.get("tags", "").split(",") if t.strip()]
        tag_str = ", ".join(tags[:4]) if tags else "—"
        lines.append(f"• **{user_id}** — {tag_str}")
    lines.append("\nReply with the exact username (e.g. `ravi.verma`) and I'll fetch the details.")
    return format_response(
        answer="\n".join(lines),
        intent="USER_SEARCH",
        confidence=0.5,
        raw_users=user_hits,
    )


class ChatEngine:
    """
    Single entry point for the enterprise chatbot.

    Usage:
        engine = ChatEngine(config, doc_store, artifact_store, user_store, embedding_service)
        result = engine.chat("How do I submit a Spark job?")
    """

    def __init__(
        self,
        config: RetrievalConfig,
        doc_store: DocumentChunkStore,
        artifact_store: ArtifactSummaryStore,
        user_store: UserProfileStore,
        embedding_service: EmbeddingService,
        llm_model: str = "gpt-4o-mini",
    ):
        self.config = config
        self.llm_model = llm_model

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)

        self.classifier = IntentClassifier(model=llm_model)
        self.rewriter = QueryRewriter(model=llm_model)
        self.doc_retriever = DocRetriever(doc_store, embedding_service)
        self.artifact_retriever = ArtifactRetriever(artifact_store, embedding_service)
        self.user_retriever = UserRetriever(user_store, embedding_service)

    def chat(self, query: str, history: Optional[List[Dict]] = None) -> Dict:
        """
        Full pipeline: classify → rewrite → retrieve → generate → format.

        Returns the output schema dict.
        """
        history = history or []

        # 1. Classify
        classification = self.classifier.classify(query)
        intent = classification["intent"]
        confidence = classification["confidence"]
        logger.info(f"Intent: {intent} ({confidence:.2f}) — '{query}'")

        # 2. Short-circuit out-of-scope queries — no retrieval or LLM generation needed
        if intent == "OUT_OF_SCOPE":
            return format_response(
                answer=_OUT_OF_SCOPE_REPLY,
                intent="OUT_OF_SCOPE",
                confidence=confidence,
            )

        # 3. Rewrite query for better embedding recall
        search_query = self.rewriter.rewrite(query)

        # 4. Route & retrieve (deterministic — sources never mixed unless HYBRID)
        doc_hits: List[Dict] = []
        artifact_hits: List[Dict] = []
        user_hits: List[Dict] = []

        if intent == "DOC_QA":
            doc_hits = self.doc_retriever.retrieve(search_query, top_k=5)
        elif intent == "ARTIFACT_SEARCH":
            artifact_hits = self.artifact_retriever.retrieve(search_query, top_k=5)
        elif intent == "USER_SEARCH":
            user_hits = self.user_retriever.retrieve(search_query, top_k=5)
        elif intent == "HYBRID":
            doc_hits = self.doc_retriever.retrieve(search_query, top_k=3)
            artifact_hits = self.artifact_retriever.retrieve(search_query, top_k=3)
            user_hits = self.user_retriever.retrieve(search_query, top_k=3)

        # 5a. Exact match — return raw user_profile from Milvus, no LLM rephrasing
        if intent == "USER_SEARCH":
            exact_hit = _find_exact_user_hit(query, user_hits)
            if exact_hit:
                profile_text = exact_hit.get("user_profile", "No profile available.")
                return format_response(
                    answer=f"**{exact_hit['user_id']}**\n\n{profile_text}",
                    intent="USER_SEARCH",
                    confidence=1.0,
                    raw_users=[exact_hit],
                    exact_match=True,
                )

        # 5b. Disambiguation: if USER_SEARCH used a partial name, ask which user
        if intent == "USER_SEARCH" and _needs_user_clarification(query, user_hits):
            return _build_clarification_response(user_hits, query)

        # 6. Build prompt
        if intent == "DOC_QA":
            messages = build_doc_qa_messages(doc_hits, query)
        elif intent == "ARTIFACT_SEARCH":
            messages = build_artifact_search_messages(artifact_hits, query)
        elif intent == "USER_SEARCH":
            messages = build_user_search_messages(user_hits, query)
        else:  # HYBRID
            messages = build_hybrid_messages(doc_hits, artifact_hits, user_hits, query)

        # Inject conversation history between system and user turn
        if history:
            messages = [messages[0]] + history + [messages[-1]]

        # 7. Generate
        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.2,
                max_tokens=600,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "I encountered an error generating a response. Please try again."

        # 8. Format
        return format_response(
            answer=answer,
            intent=intent,
            confidence=confidence,
            raw_artifacts=artifact_hits,
            raw_users=user_hits,
            raw_docs=doc_hits,
        )
