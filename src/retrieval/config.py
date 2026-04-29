"""Configuration management for the retrieval system."""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env from project root (or any parent directory) automatically.
# This means callers do not need to set env vars manually in development.
load_dotenv(override=True)


class RetrievalConfig(BaseModel):
    """Configuration for the vector retrieval system."""

    # Milvus
    milvus_host: str = Field(default="localhost")
    milvus_port: int = Field(default=19530)
    collection_name: str = Field(default="kubeflow_artifacts")

    # Embedding — OpenAI text-embedding-3-small (1536-dim)
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536)

    # Processing
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    batch_size: int = Field(default=32)   # max inputs per OpenAI embeddings request

    # Search
    similarity_metric: str = Field(default="COSINE")
    default_top_k: int = Field(default=10)
    index_type: str = Field(default="HNSW")

    # Catalog path — must point to ingestion_catalog.json
    ingestion_catalog_path: str = Field(default="dataset/.ingestion/ingestion_catalog.json")

    @classmethod
    def from_env(cls) -> "RetrievalConfig":
        """Create config from environment variables (after .env is loaded)."""
        return cls(
            milvus_host=os.getenv("MILVUS_HOST", "localhost"),
            milvus_port=int(os.getenv("MILVUS_PORT", "19530")),
            collection_name=os.getenv("MILVUS_COLLECTION", "kubeflow_artifacts"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
            batch_size=int(os.getenv("BATCH_SIZE", "32")),
            ingestion_catalog_path=os.getenv(
                "INGESTION_CATALOG_PATH",
                "dataset/.ingestion/ingestion_catalog.json",
            ),
        )


config = RetrievalConfig.from_env()
