"""Shared pytest fixtures for the document pipeline test suite."""

import pytest

from document_pipeline.config.settings import PipelineSettings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
  """Ensure settings cache does not leak between tests."""
  get_settings.cache_clear()
  yield
  get_settings.cache_clear()


@pytest.fixture
def pipeline_settings() -> PipelineSettings:
  """Provide a default PipelineSettings instance for tests."""
  return PipelineSettings()


@pytest.fixture
def document_loader():
  """Provide a concrete DocumentLoader instance."""
  from document_pipeline.pipeline.stages.loader import DocumentLoader

  return DocumentLoader()


@pytest.fixture
def document_cleaner():
  """Provide a concrete DocumentCleaner instance."""
  from document_pipeline.pipeline.stages.cleaner import DocumentCleaner

  return DocumentCleaner()


@pytest.fixture
def section_extractor():
  """Provide a concrete SectionExtractor instance."""
  from document_pipeline.pipeline.stages.section_extractor import SectionExtractor

  return SectionExtractor()


@pytest.fixture
def block_extractor():
  """Provide a concrete DocumentBlockExtractor instance."""
  from document_pipeline.pipeline.stages.block_extractor import DocumentBlockExtractor

  return DocumentBlockExtractor()


@pytest.fixture
def clause_builder():
  """Provide a concrete ClauseBuilder instance."""
  from document_pipeline.pipeline.stages.clause_builder import ClauseBuilder

  return ClauseBuilder()


@pytest.fixture
def clause_extractor():
  """Provide a concrete ClauseExtractor instance."""
  from document_pipeline.pipeline.stages.clause_extractor import ClauseExtractor

  return ClauseExtractor()


@pytest.fixture
def document_understanding():
  """Provide a concrete DocumentUnderstanding instance."""
  from document_pipeline.pipeline.stages.document_understanding import (
    DocumentUnderstanding,
  )

  return DocumentUnderstanding()
