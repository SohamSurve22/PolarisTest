"""Tests for core abstractions."""

from abc import ABC

from document_pipeline.core.base import BaseProcessor


def test_base_processor_is_abstract() -> None:
  """BaseProcessor cannot be instantiated directly."""
  assert issubclass(BaseProcessor, ABC)
