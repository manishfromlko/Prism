"""
Chatbot engine — orchestrates: classify → rewrite → retrieve → generate → format.

classify   →  IntentClassifier
rewrite    →  QueryRewriter
retrieve   →  DocRetriever | ArtifactRetriever | UserRetriever (or all for HYBRID)
resolve    →  UserNameResolver  (name disambiguation before any vector search)
generate   →  OpenAI chat completion with per-intent prompt template
format     →  formatter.format_response

USER_SEARCH flow:
  1. String-match + RapidFuzz against full user roster (no vector search)
  2. Single high-confidence hit → fetch raw profile from Milvus, return (no LLM)
  3. Multiple/ambiguous → LLM disambiguation (no vector search)
  4. Zero hits → fall through to vector retrieval (semantic query like "who works on NLP?")
"""

import logging
from typing import Dict, List, Optional

from ..artifact_summary_store import ArtifactSummaryStore
from ..config import RetrievalConfig, make_openai_client
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
from .user_resolver import UserNameResolver, retrieve_candidates

logger = logging.getLogger(__name__)

_OUT_OF_SCOPE_REPLY = (
    "That's outside what I can help with — I don't have access to real-time or external information.\n\n"
    "I'm designed to assist with:\n"
    "• **Platform docs** — how-to guides, onboarding, concepts\n"
    "• **Artifact discovery** — finding notebooks, scripts, and code examples\n"
    "• **People search** — finding colleagues by expertise or what they're working on\n\n"
    "Try asking something like: *\"How do I submit a Spark job?\"* or *\"Who works on NLP?\"*"
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

        self.client = make_openai_client()

        self.user_store = user_store
        self.classifier = IntentClassifier(model=llm_model)
        self.rewriter = QueryRewriter(model=llm_model)
        self.doc_retriever = DocRetriever(doc_store, embedding_service)
        self.artifact_retriever = ArtifactRetriever(artifact_store, embedding_service)
        self.user_retriever = UserRetriever(user_store, embedding_service)
        self.user_resolver = UserNameResolver(user_store, model=llm_model)

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

        # 2. Short-circuit out-of-scope queries
        if intent == "OUT_OF_SCOPE":
            return format_response(
                answer=_OUT_OF_SCOPE_REPLY,
                intent="OUT_OF_SCOPE",
                confidence=confidence,
            )

        # 3. Rewrite query for better embedding recall
        search_query = self.rewriter.rewrite(query)

        # 4. USER_SEARCH: name resolution first, vector retrieval only as fallback
        if intent == "USER_SEARCH":
            all_ids = self.user_store.get_all_user_ids()
            name_candidates = retrieve_candidates(query, all_ids)

            if name_candidates:
                # Name lookup path — resolve, then fetch from Milvus if exact
                resolved = self.user_resolver.resolve(query, candidates=name_candidates)
                if resolved.get("exact_uid"):
                    uid = resolved["exact_uid"]
                    profile = self.user_store.get_profile(uid)
                    if profile:
                        return format_response(
                            answer=f"**{uid}**\n\n{profile['user_profile']}",
                            intent="USER_SEARCH",
                            confidence=1.0,
                            raw_users=[profile],
                            exact_match=True,
                        )
                return format_response(
                    answer=resolved["answer"],
                    intent="USER_SEARCH",
                    confidence=0.5,
                )
            # No name match — fall through to semantic vector search below

        # 5. Route & retrieve for non-name-lookup paths
        doc_hits: List[Dict] = []
        artifact_hits: List[Dict] = []
        user_hits: List[Dict] = []

        if intent == "DOC_QA":
            doc_hits = self.doc_retriever.retrieve(search_query, top_k=5)
        elif intent == "ARTIFACT_SEARCH":
            artifact_hits = self.artifact_retriever.retrieve(search_query, top_k=5)
        elif intent == "USER_SEARCH":
            # Semantic query: "who works on NLP?" — no name tokens matched
            user_hits = self.user_retriever.retrieve(search_query, top_k=5)
        elif intent == "HYBRID":
            doc_hits = self.doc_retriever.retrieve(search_query, top_k=3)
            artifact_hits = self.artifact_retriever.retrieve(search_query, top_k=3)
            user_hits = self.user_retriever.retrieve(search_query, top_k=3)

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
