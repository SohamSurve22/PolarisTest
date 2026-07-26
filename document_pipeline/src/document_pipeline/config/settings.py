"""Pipeline configuration loaded from environment and defaults."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
  """Application-wide settings for the document intelligence pipeline.

  Values can be overridden via environment variables prefixed with ``PIPELINE_``.
  """

  model_config = SettingsConfigDict(
    env_prefix="PIPELINE_",
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
  )

  app_name: str = Field(default="PolarisLex Document Pipeline")
  log_level: str = Field(default="INFO")
  log_format: str = Field(
    default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
  )

  data_dir: Path = Field(default=Path("data"))
  uploads_dir: Path = Field(default=Path("data/uploads"))
  processed_dir: Path = Field(default=Path("data/processed"))

  # Stage toggles (for future selective execution)
  enable_cleaning: bool = Field(default=True)
  enable_section_extraction: bool = Field(default=True)
  enable_clause_extraction: bool = Field(default=True)
  enable_llm_preparation: bool = Field(default=True)


@lru_cache
def get_settings() -> PipelineSettings:
  """Return a cached singleton instance of pipeline settings."""
  return PipelineSettings()
