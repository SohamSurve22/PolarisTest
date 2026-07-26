"""Tests for pipeline data models."""

import re

from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.utils.document_ids import generate_document_id


def test_document_source_creation() -> None:
  """DocumentSource accepts valid metadata."""
  metadata = DocumentMetadata(
    document_id="doc-001",
    filename="contract.pdf",
    format=DocumentFormat.PDF,
  )
  source = DocumentSource(metadata=metadata)
  assert source.metadata.document_id == "doc-001"
  assert source.encoding == "utf-8"


def test_document_metadata_generates_stable_document_id() -> None:
  """DocumentMetadata auto-generates a DOC_ prefixed identifier when omitted."""
  metadata = DocumentMetadata(
    filename="contract.pdf",
    format=DocumentFormat.PDF,
  )

  assert re.fullmatch(r"DOC_[0-9a-f]{8}", metadata.document_id)


def test_generate_document_id_format() -> None:
  """Generated document IDs follow the DOC_xxxxxxxx pattern."""
  document_id = generate_document_id()

  assert re.fullmatch(r"DOC_[0-9a-f]{8}", document_id)


def test_span_length() -> None:
  """Span length is computed from start and end offsets."""
  span = Span(start=10, end=25)
  assert len(span) == 15
