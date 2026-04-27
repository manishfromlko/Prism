"""Configuration management for the retrieval system."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    """Configuration for the vector retrieval system."""

    # Milvus configuration
    milvus_host: str = Field(default="localhost", description="Milvus server host")
    milvus_port: int = Field(default=19530, description="Milvus server port")
    collection_name: str = Field(default="kubeflow_artifacts", description="Milvus collection name")

    # Embedding configuration
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model name"
    )
    embedding_dimension: int = Field(default=384, description="Embedding vector dimension")

    # Processing configuration
    chunk_size: int = Field(default=1000, description="Text chunk size for splitting")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")
    batch_size: int = Field(default=32, description="Batch size for processing")

    # Search configuration
    similarity_metric: str = Field(default="COSINE", description="Similarity metric for search")
    default_top_k: int = Field(default=10, description="Default number of results")
    index_type: str = Field(default="HNSW", description="Vector index type")

    @classmethod
    def from_env(cls) -> "RetrievalConfig":
        """Create config from environment variables."""
        return cls(
            milvus_host=os.getenv("MILVUS_HOST", "localhost"),
            milvus_port=int(os.getenv("MILVUS_PORT", "19530")),
            collection_name=os.getenv("MILVUS_COLLECTION", "kubeflow_artifacts"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            batch_size=int(os.getenv("BATCH_SIZE", "32")),
        )


# Global config instance
config = RetrievalConfig.from_env()