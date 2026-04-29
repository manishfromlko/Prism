"""Langchain retriever implementations for vector search."""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import BaseModel, Field

from .config import RetrievalConfig
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class VectorRetriever(BaseRetriever):
    """Langchain retriever for vector similarity search."""

    vector_store: VectorStore = Field(...)
    config: RetrievalConfig = Field(...)

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
        **kwargs
    ) -> List[Document]:
        """Retrieve relevant documents for a query.

        Args:
            query: Search query
            run_manager: Callback manager

        Returns:
            List of relevant documents
        """
        try:
            # Generate query embedding
            from .embeddings import EmbeddingService
            embedder = EmbeddingService(self.config)
            query_vector = embedder.generate_embedding(query)

            # Search vectors
            top_k = kwargs.get('top_k', self.config.default_top_k)
            results = self.vector_store.search_vectors(query_vector, top_k=top_k)

            # Convert to Langchain documents
            documents = []
            for result in results:
                doc = Document(
                    page_content=result['content'],
                    metadata={
                        'artifact_id': result['artifact_id'],
                        'score': result['score'],
                        'id': result['id'],
                        **result['metadata']
                    }
                )
                documents.append(doc)

            logger.info(f"Retrieved {len(documents)} documents for query: {query[:50]}...")
            return documents

        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            return []


class HybridRetriever(BaseRetriever):
    """Hybrid retriever combining vector and keyword search."""

    vector_store: VectorStore = Field(...)
    config: RetrievalConfig = Field(...)
    keyword_weight: float = Field(default=0.3)
    vector_weight: float = Field(default=0.7)

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
        **kwargs
    ) -> List[Document]:
        """Retrieve documents using hybrid search.

        Args:
            query: Search query
            run_manager: Callback manager

        Returns:
            List of relevant documents
        """
        try:
            # Get vector results
            vector_docs = self._vector_search(query, **kwargs)

            # Get keyword results (simplified - could use BM25 or similar)
            keyword_docs = self._keyword_search(query, **kwargs)

            # Combine and rerank
            combined = self._combine_results(vector_docs, keyword_docs)

            logger.info(f"Hybrid search returned {len(combined)} documents")
            return combined

        except Exception as e:
            logger.error(f"Failed hybrid retrieval: {e}")
            return []

    def _vector_search(self, query: str, **kwargs) -> List[Document]:
        """Perform vector search."""
        retriever = VectorRetriever(vector_store=self.vector_store, config=self.config)
        return retriever._get_relevant_documents(query, run_manager=None, **kwargs)

    def _keyword_search(self, query: str, **kwargs) -> List[Document]:
        """Perform keyword-based search (simplified implementation)."""
        # This is a simplified keyword search
        # In production, you might use BM25, TF-IDF, or integrate with search engines

        query_terms = set(query.lower().split())
        top_k = kwargs.get('top_k', self.config.default_top_k)

        # Get all documents (inefficient for large collections)
        # In practice, you'd want to index content for keyword search
        try:
            # This is a placeholder - real implementation would need content indexing
            results = self.vector_store.search_vectors([0.0] * self.config.embedding_dimension, top_k=100)

            scored_docs = []
            for result in results:
                content = result['content'].lower()
                score = sum(1 for term in query_terms if term in content)
                if score > 0:
                    doc = Document(
                        page_content=result['content'],
                        metadata={
                            'artifact_id': result['artifact_id'],
                            'keyword_score': score,
                            'id': result['id'],
                            **result['metadata']
                        }
                    )
                    scored_docs.append((doc, score))

            # Sort by keyword score and take top_k
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in scored_docs[:top_k]]

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _combine_results(self, vector_docs: List[Document], keyword_docs: List[Document]) -> List[Document]:
        """Combine and rerank vector and keyword results."""
        # Create score mapping
        doc_scores = {}

        # Add vector scores
        for doc in vector_docs:
            key = doc.metadata['artifact_id']
            doc_scores[key] = {
                'doc': doc,
                'vector_score': doc.metadata.get('score', 0.0),
                'keyword_score': 0.0
            }

        # Add keyword scores
        for doc in keyword_docs:
            key = doc.metadata['artifact_id']
            if key in doc_scores:
                doc_scores[key]['keyword_score'] = doc.metadata.get('keyword_score', 0.0)
            else:
                doc_scores[key] = {
                    'doc': doc,
                    'vector_score': 0.0,
                    'keyword_score': doc.metadata.get('keyword_score', 0.0)
                }

        # Calculate combined scores
        for key, data in doc_scores.items():
            combined_score = (
                self.vector_weight * data['vector_score'] +
                self.keyword_weight * data['keyword_score']
            )
            data['combined_score'] = combined_score
            data['doc'].metadata['combined_score'] = combined_score

        # Sort by combined score
        sorted_docs = sorted(
            doc_scores.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )

        return [data['doc'] for data in sorted_docs]


class QueryProcessor:
    """Processor for query expansion and refinement."""

    def __init__(self, config: RetrievalConfig):
        """Initialize query processor.

        Args:
            config: Retrieval configuration
        """
        self.config = config

    def expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms and related terms.

        Args:
            query: Original query

        Returns:
            List of expanded queries
        """
        # Simple expansion - in production, use word embeddings or knowledge graphs
        expansions = [query]

        # Add common synonyms
        synonyms = {
            'machine learning': ['ml', 'ai', 'artificial intelligence'],
            'data': ['dataset', 'information', 'records'],
            'model': ['algorithm', 'classifier', 'predictor'],
            'training': ['learning', 'fitting', 'optimization'],
        }

        for term, syns in synonyms.items():
            if term in query.lower():
                for syn in syns:
                    expanded = query.lower().replace(term, syn)
                    expansions.append(expanded.title())

        return list(set(expansions))  # Remove duplicates

    def refine_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Refine query based on context.

        Args:
            query: Original query
            context: Additional context information

        Returns:
            Refined query
        """
        refined = query

        # Add context-based terms
        if context:
            workspace = context.get('workspace')
            if workspace:
                refined += f" in {workspace}"

            artifact_type = context.get('type')
            if artifact_type:
                refined += f" {artifact_type}"

        return refined


class RetrievalEvaluator:
    """Evaluator for retrieval quality metrics."""

    def __init__(self, config: RetrievalConfig):
        """Initialize evaluator.

        Args:
            config: Retrieval configuration
        """
        self.config = config

    def evaluate_retrieval(
        self,
        queries: List[str],
        ground_truth: List[List[str]],
        retriever: BaseRetriever
    ) -> Dict[str, float]:
        """Evaluate retrieval quality.

        Args:
            queries: List of test queries
            ground_truth: List of relevant artifact IDs for each query
            retriever: Retriever to evaluate

        Returns:
            Dictionary with evaluation metrics
        """
        total_precision = 0.0
        total_recall = 0.0
        total_f1 = 0.0

        for query, truth in zip(queries, ground_truth):
            try:
                results = retriever._get_relevant_documents(query, run_manager=None)
                retrieved_ids = [doc.metadata['artifact_id'] for doc in results]

                # Calculate metrics
                precision = self._calculate_precision(truth, retrieved_ids)
                recall = self._calculate_recall(truth, retrieved_ids)
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

                total_precision += precision
                total_recall += recall
                total_f1 += f1

            except Exception as e:
                logger.error(f"Failed to evaluate query '{query}': {e}")

        num_queries = len(queries)
        return {
            'avg_precision': total_precision / num_queries,
            'avg_recall': total_recall / num_queries,
            'avg_f1': total_f1 / num_queries,
        }

    def _calculate_precision(self, relevant: List[str], retrieved: List[str]) -> float:
        """Calculate precision."""
        if not retrieved:
            return 0.0
        relevant_set = set(relevant)
        retrieved_set = set(retrieved)
        return len(relevant_set & retrieved_set) / len(retrieved_set)

    def _calculate_recall(self, relevant: List[str], retrieved: List[str]) -> float:
        """Calculate recall."""
        if not relevant:
            return 1.0 if not retrieved else 0.0
        relevant_set = set(relevant)
        retrieved_set = set(retrieved)
        return len(relevant_set & retrieved_set) / len(relevant_set)