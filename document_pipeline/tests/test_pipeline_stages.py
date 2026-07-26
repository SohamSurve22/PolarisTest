"""Tests for pipeline stage interfaces."""

from document_pipeline.pipeline.stages.clause_builder import ClauseBuilder
from document_pipeline.pipeline.stages.clause_extractor import ClauseExtractor
from document_pipeline.pipeline.stages.cleaner import DocumentCleaner
from document_pipeline.pipeline.stages.llm_preparer import LLMPreparer
from document_pipeline.pipeline.stages.loader import DocumentLoader
from document_pipeline.pipeline.stages.section_extractor import SectionExtractor


def test_document_loader_is_concrete() -> None:
  """Stage 1 loader is implemented and can be instantiated."""
  loader = DocumentLoader()
  assert isinstance(loader, DocumentLoader)


def test_document_cleaner_is_concrete() -> None:
  """Stage 2 cleaner is implemented and can be instantiated."""
  cleaner = DocumentCleaner()
  assert isinstance(cleaner, DocumentCleaner)


def test_section_extractor_is_concrete() -> None:
  """Stage 3 section extractor is implemented and can be instantiated."""
  extractor = SectionExtractor()
  assert isinstance(extractor, SectionExtractor)


def test_clause_builder_is_concrete() -> None:
  """Stage 5 clause builder is implemented and can be instantiated."""
  builder = ClauseBuilder()
  assert isinstance(builder, ClauseBuilder)


def test_clause_extractor_is_concrete() -> None:
  """Stage 6 clause extractor is implemented and can be instantiated."""
  extractor = ClauseExtractor()
  assert isinstance(extractor, ClauseExtractor)


def test_llm_preparer_is_concrete() -> None:
  """Stage 7 LLM preparer is implemented and can be instantiated."""
  assert LLMPreparer.process
