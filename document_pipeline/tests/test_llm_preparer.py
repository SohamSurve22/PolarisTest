"""Tests for LLM preparation stage."""

from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.context_builder import ContextBuilder
from document_pipeline.pipeline.stages.document_understanding import DocumentUnderstanding
from document_pipeline.pipeline.stages.entity_extractor import EntityExtractor
from document_pipeline.pipeline.stages.llm_preparer import DefaultLLMPreparer
from document_pipeline.models.clause import Clause, SegmentedDocument
from document_pipeline.models.metadata import Span


def _segmented_document(text: str) -> SegmentedDocument:
  metadata = DocumentMetadata(
    document_id="DOC_test",
    filename="policy.txt",
    format=DocumentFormat.TXT,
  )
  clause = Clause(
    clause_id="S001_C001",
    document_id="DOC_test",
    document_type=DocumentFormat.TXT,
    section_id="S001",
    section_title="Scope",
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )
  return SegmentedDocument(metadata=metadata, clauses=[clause])


def test_default_llm_preparer_builds_chunks_with_context() -> None:
  segmented = _segmented_document(
    "The Data Fiduciary shall process personal data within 30 days.",
  )
  classified = DocumentUnderstanding().process(segmented)
  context = ContextBuilder().process(classified)
  entity_doc = EntityExtractor().process(context)

  semantic = DefaultLLMPreparer().process(entity_doc)

  assert len(semantic.chunks) == 1
  chunk = semantic.chunks[0]
  assert chunk.clause_id == "S001_C001"
  assert "Data Fiduciary" in chunk.context.get("entities", "")
  assert chunk.token_estimate is not None and chunk.token_estimate > 0
