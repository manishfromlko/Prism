"""
Drop-in replacement for src/retrieval/vector_store.py in a Databricks environment.

Uses Databricks Vector Search (managed embeddings) instead of Milvus.
The index must be created with embedding_source_column pointing at the text field
so that similarity_search() accepts query_text (not a raw vector).
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ENDPOINT = os.getenv("VECTOR_SEARCH_ENDPOINT", "kubeflow-intelligence-endpoint")

# Index names — match the Delta tables created in the setup notebooks
ARTIFACT_CHUNKS_INDEX    = "kubeflow.intelligence.artifact_chunks_index"
ARTIFACT_SUMMARIES_INDEX = "kubeflow.intelligence.artifact_summaries_index"
USER_PROFILES_INDEX      = "kubeflow.intelligence.user_profiles_index"


class DatabricksVectorStore:
    """Wraps a single Databricks Vector Search index."""

    def __init__(self, index_name: str):
        from databricks.vector_search.client import VectorSearchClient
        vsc = VectorSearchClient(
            workspace_url=os.environ["DATABRICKS_HOST"],
            personal_access_token=os.environ["DATABRICKS_TOKEN"],
        )
        self.index = vsc.get_index(ENDPOINT, index_name)
        self.index_name = index_name
        logger.info(f"DatabricksVectorStore ready: {index_name}")

    def search(
        self,
        query_text: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """
        Similarity search using managed embeddings.
        Returns list of row dicts (same column names as the source Delta table).
        """
        try:
            response = self.index.similarity_search(
                query_text=query_text,
                columns=["*"],
                num_results=top_k,
                filters=filters,
            )
            rows = response.get("result", {}).get("data_array", [])
            columns = response.get("result", {}).get("manifest", {}).get("columns", [])
            col_names = [c["name"] for c in columns]
            return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            logger.error(f"Vector search failed on {self.index_name}: {e}")
            return []

    def get_all_ids(self, id_column: str) -> List[str]:
        """Fetch all primary-key values (used by UserNameResolver)."""
        try:
            response = self.index.similarity_search(
                query_text="*",
                columns=[id_column],
                num_results=10_000,
            )
            rows = response.get("result", {}).get("data_array", [])
            columns = response.get("result", {}).get("manifest", {}).get("columns", [])
            col_names = [c["name"] for c in columns]
            idx = col_names.index(id_column)
            return [row[idx] for row in rows]
        except Exception as e:
            logger.error(f"get_all_ids failed on {self.index_name}: {e}")
            return []
