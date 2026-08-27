"""Vectorization configuration loaded from environment and defaults."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VectorizationSettings(BaseSettings):
  """Application-wide settings for the embedding pipeline.

  Values can be overridden via environment variables prefixed with
  ``VECTORIZATION_``, or via a ``.env`` file. Nothing here should ever
  be a literal credential in code — that was the problem with the old
  ``vectorization.py`` script.
  """

  model_config = SettingsConfigDict(
    env_prefix="VECTORIZATION_",
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
  )

  app_name: str = Field(default="PolarisLex Vectorization")
  log_level: str = Field(default="INFO")

  # --- Postgres / pgvector ---
  pg_host: str = Field(default="localhost")
  pg_port: int = Field(default=5432)
  pg_database: str = Field(default="polarislex")
  pg_user: str = Field(default="polarislex")
  pg_password: str = Field(default="")
  pg_table: str = Field(default="legal_documents_vectorization")

  # --- Embedding model (Ollama) ---
  ollama_url: str = Field(default="http://localhost:11434/api/embeddings")
  embedding_model: str = Field(default="nomic-embed-text")
  embedding_dim: int = Field(default=768)

  # --- Local LLM (retrieval-text generation, via semantic_graph) ---
  # 7B q4 is the sizing sweet spot for 16GB unified memory — see README.
  enable_retrieval_summarization: bool = Field(default=True)
  local_llm_model: str = Field(default="qwen2.5:7b-instruct-q4_K_M")

  # --- Source data ---
  # Where document_pipeline writes its SegmentedDocument JSON files.
  clauses_dir: str = Field(default="../document_pipeline/output")

  # --- Batching / resilience ---
  batch_size: int = Field(default=50)
  request_timeout_seconds: float = Field(default=30.0)


@lru_cache
def get_settings() -> VectorizationSettings:
  """Return a cached singleton instance of vectorization settings."""
  return VectorizationSettings()
