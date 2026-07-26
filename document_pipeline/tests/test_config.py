"""Tests for centralized configuration."""

from document_pipeline.config.settings import PipelineSettings, get_settings


def test_default_settings() -> None:
  """Default settings provide expected values."""
  settings = PipelineSettings()
  assert settings.app_name == "PolarisLex Document Pipeline"
  assert settings.log_level == "INFO"
  assert settings.enable_cleaning is True


def test_settings_singleton() -> None:
  """get_settings returns a cached instance."""
  assert get_settings() is get_settings()
