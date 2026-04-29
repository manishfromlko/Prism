"""Milvus vector store integration for storing and retrieving embeddings."""

import logging
from typing import Any, Dict, List, Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from .config import RetrievalConfig

logger = logging.getLogger(__name__)


class VectorStore:
    """Milvus-based vector store for embeddings."""

    def __init__(self, config: RetrievalConfig):
        """Initialize the vector store.

        Args:
            config: Retrieval configuration
        """
        self.config = config
        self.collection: Optional[Collection] = None
        self._collection_loaded = False
        self._connect()

    def _connect(self) -> None:
        """Connect to Milvus server."""
        try:
            logger.info(f"Connecting to Milvus at {self.config.milvus_host}:{self.config.milvus_port}")
            connections.connect(
                alias="default",
                host=self.config.milvus_host,
                port=self.config.milvus_port
            )
            logger.info("Connected to Milvus successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise

    def create_collection(self, drop_if_exists: bool = False) -> None:
        """Create the vector collection with proper schema.

        Args:
            drop_if_exists: Whether to drop existing collection
        """
        if drop_if_exists and utility.has_collection(self.config.collection_name):
            logger.info(f"Dropping existing collection: {self.config.collection_name}")
            utility.drop_collection(self.config.collection_name)

        if not utility.has_collection(self.config.collection_name):
            logger.info(f"Creating collection: {self.config.collection_name}")

            # Define schema
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.INT64,
                    is_primary=True,
                    auto_id=True
                ),
                FieldSchema(
                    name="artifact_id",
                    dtype=DataType.VARCHAR,
                    max_length=255
                ),
                FieldSchema(
                    name="vector",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.config.embedding_dimension
                ),
                FieldSchema(
                    name="content",
                    dtype=DataType.VARCHAR,
                    max_length=5000
                ),
                FieldSchema(
                    name="metadata",
                    dtype=DataType.JSON
                ),
            ]

            schema = CollectionSchema(
                fields=fields,
                description="Kubeflow workspace artifacts vector collection"
            )

            self.collection = Collection(
                name=self.config.collection_name,
                schema=schema,
                using="default"
            )

            # Create index
            index_params = {
                "metric_type": self.config.similarity_metric,
                "index_type": self.config.index_type,
                "params": {"M": 16, "efConstruction": 256}
            }

            self.collection.create_index(
                field_name="vector",
                index_params=index_params
            )

            logger.info("Collection created and indexed")
        else:
            logger.info(f"Collection {self.config.collection_name} already exists")
            self.collection = Collection(self.config.collection_name)

    def insert_vectors(
        self,
        artifact_ids: List[str],
        vectors: List[List[float]],
        contents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> List[int]:
        """Insert vectors into the collection.

        Args:
            artifact_ids: List of artifact identifiers
            vectors: List of embedding vectors
            contents: List of content snippets
            metadatas: List of metadata dictionaries

        Returns:
            List of inserted entity IDs
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            logger.info(f"Inserting {len(vectors)} vectors")

            # Prepare data
            data = [
                artifact_ids,
                vectors,
                contents,
                metadatas
            ]

            # Insert data
            result = self.collection.insert(data)
            self.collection.flush()

            logger.info(f"Inserted {len(result.primary_keys)} entities")
            return result.primary_keys

        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            raise

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results with scores and metadata
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            # Load collection into memory only once per process lifetime
            if not self._collection_loaded:
                self.collection.load()
                self._collection_loaded = True

            # Prepare search parameters
            search_params = {"metric_type": self.config.similarity_metric, "params": {"ef": 128}}

            # Build filter expression if provided
            expr = None
            if filters:
                # Simple filter example - can be extended
                filter_conditions = []
                for key, value in filters.items():
                    if isinstance(value, str):
                        filter_conditions.append(f'{key} == "{value}"')
                    else:
                        filter_conditions.append(f'{key} == {value}')
                if filter_conditions:
                    expr = " and ".join(filter_conditions)

            # Search
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["artifact_id", "content", "metadata"]
            )

            # Format results
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        "artifact_id": hit.entity.get("artifact_id"),
                        "content": hit.entity.get("content"),
                        "metadata": hit.entity.get("metadata"),
                        "score": hit.score,
                        "id": hit.id
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics.

        Returns:
            Dictionary with collection stats
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            stats = {
                "name": self.collection.name,
                "num_entities": self.collection.num_entities,
                "schema": str(self.collection.schema),
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise

    def update_vectors(
        self,
        artifact_ids: List[str],
        vectors: List[List[float]],
        contents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> int:
        """Update existing vectors in the collection.

        Args:
            artifact_ids: List of artifact identifiers to update
            vectors: List of new embedding vectors
            contents: List of new content snippets
            metadatas: List of new metadata dictionaries

        Returns:
            Number of vectors updated
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            # First, delete existing vectors
            expr = f"artifact_id in {artifact_ids}"
            delete_result = self.collection.delete(expr)
            logger.info(f"Deleted {delete_result.delete_count} existing vectors")

            # Then insert new ones
            insert_count = self.insert_vectors(artifact_ids, vectors, contents, metadatas)

            return insert_count

        except Exception as e:
            logger.error(f"Failed to update vectors: {e}")
            raise

    def delete_vectors(self, artifact_ids: List[str]) -> int:
        """Delete vectors by artifact IDs.

        Args:
            artifact_ids: List of artifact identifiers to delete

        Returns:
            Number of vectors deleted
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            expr = f"artifact_id in {artifact_ids}"
            result = self.collection.delete(expr)
            self.collection.flush()
            logger.info(f"Deleted {result.delete_count} vectors")
            return result.delete_count
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise

    def get_vector_count(self) -> int:
        """Get the total number of vectors in the collection.

        Returns:
            Number of vectors
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        return self.collection.num_entities

    def backup_collection(self, backup_path: str) -> None:
        """Backup collection data to a file.

        Args:
            backup_path: Path to save backup
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            if not self._collection_loaded:
                self.collection.load()
                self._collection_loaded = True
            results = self.collection.query(
                expr="id >= 0",  # Get all
                output_fields=["artifact_id", "vector", "content", "metadata"]
            )

            # Save to file
            import json
            with open(backup_path, 'w') as f:
                json.dump(results, f, indent=2)

            logger.info(f"Backed up {len(results)} vectors to {backup_path}")

        except Exception as e:
            logger.error(f"Failed to backup collection: {e}")
            raise

    def restore_collection(self, backup_path: str) -> int:
        """Restore collection data from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            Number of vectors restored
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            import json
            with open(backup_path, 'r') as f:
                data = json.load(f)

            # Extract data for insertion
            artifact_ids = [item['artifact_id'] for item in data]
            vectors = [item['vector'] for item in data]
            contents = [item['content'] for item in data]
            metadatas = [item['metadata'] for item in data]

            # Insert data
            count = self.insert_vectors(artifact_ids, vectors, contents, metadatas)
            logger.info(f"Restored {count} vectors from {backup_path}")

            return count

        except Exception as e:
            logger.error(f"Failed to restore collection: {e}")
            raise

    def optimize_index(self) -> None:
        """Optimize the vector index for better search performance."""
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            # Rebuild index with optimized parameters
            self.collection.drop_index()
            index_params = {
                "metric_type": self.config.similarity_metric,
                "index_type": self.config.index_type,
                "params": {
                    "M": 16,
                    "efConstruction": 256,
                    "ef": 128  # Higher ef for better recall
                }
            }
            self.collection.create_index(
                field_name="vector",
                index_params=index_params
            )
            logger.info("Index optimized")
        except Exception as e:
            logger.error(f"Failed to optimize index: {e}")
            raise

    def get_index_info(self) -> Dict[str, Any]:
        """Get information about the vector index.

        Returns:
            Index information dictionary
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        try:
            index_info = self.collection.index()
            return {
                "index_type": index_info.params.get("index_type"),
                "metric_type": index_info.params.get("metric_type"),
                "params": index_info.params,
            }
        except Exception as e:
            logger.error(f"Failed to get index info: {e}")
            raise