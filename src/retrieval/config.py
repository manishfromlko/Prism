"""Configuration management for the retrieval system."""

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from ..observability import make_llm_client

# Load .env from project root (or any parent directory) automatically.
# This means callers do not need to set env vars manually in development.
load_dotenv(override=True)


class RetrievalConfig(BaseModel):
    """Configuration for the vector retrieval system."""

    # Qdrant
    qdrant_host: str = Field(default="127.0.0.1")
    qdrant_port: int = Field(default=6333)
    qdrant_api_key: Optional[str] = Field(default=None)
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

    # LLM for user profile generation (chat completion, not embeddings)
    profile_llm_model: str = Field(default="gpt-4o-mini")

    # Chat runtime
    chat_agent_mode: str = Field(default="legacy")
    agent_max_steps: int = Field(default=4)
    agent_enable_planner_llm: bool = Field(default=False)

    @classmethod
    def from_env(cls) -> "RetrievalConfig":
        """Create config from environment variables (after .env is loaded)."""
        return cls(
            qdrant_host=os.getenv("QDRANT_HOST", "127.0.0.1"),
            qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            collection_name=os.getenv("QDRANT_COLLECTION", "kubeflow_artifacts"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            batch_size=int(os.getenv("BATCH_SIZE", "32")),
            ingestion_catalog_path=os.getenv(
                "INGESTION_CATALOG_PATH",
                "dataset/.ingestion/ingestion_catalog.json",
            ),
            profile_llm_model=os.getenv("PROFILE_LLM_MODEL", "gpt-4o-mini"),
            chat_agent_mode=os.getenv("CHAT_AGENT_MODE", "legacy"),
            agent_max_steps=int(os.getenv("AGENT_MAX_STEPS", "4")),
            agent_enable_planner_llm=os.getenv(
                "AGENT_ENABLE_PLANNER_LLM",
                "false",
            ).lower() in {"1", "true", "yes", "on"},
        )


config = RetrievalConfig.from_env()


def make_openai_client() -> OpenAI:
    """Return a direct OpenAI client with LangSmith tracing when enabled."""
    return make_llm_client()
