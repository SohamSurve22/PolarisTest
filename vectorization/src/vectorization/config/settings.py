"""Vectorization configuration loaded from environment and defaults."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VectorizationSettings(BaseSettings):
  """Application-wide settings for the embedding pipeline.

  Values can be overridden via environment variables prefixed with
  ``VECTORIZATION_``, or via a ``.env`` file. Nothing here should ever
  be a literal credential in code.
  """

  model_config = SettingsConfigDict(
    env_prefix="VECTORIZATION_",
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
  )

  app_name: str = Field(default="PolarisLex Vectorization")
  log_level: str = Field(default="INFO")

  # --- Qdrant ---
  qdrant_url: str = Field(default="http://localhost:6333")
  qdrant_collection: str = Field(default="document_clauses")

  # --- Embedding model (Ollama) ---
  ollama_url: str = Field(default="http://localhost:11434/api/embeddings")
  embedding_model: str = Field(default="nomic-embed-text")
  embedding_dim: int = Field(default=768)

  # --- Source data ---
  # Where document_pipeline writes its DOC_*.json preview files.
  # Relative paths are resolved from the process working directory.
  clauses_dir: str = Field(default="../document_pipeline/output")

  # --- Batching / resilience ---
  batch_size: int = Field(default=50)
  request_timeout_seconds: float = Field(default=30.0)


@lru_cache
def get_settings() -> VectorizationSettings:
  """Return a cached singleton instance of vectorization settings."""
  return VectorizationSettings()
