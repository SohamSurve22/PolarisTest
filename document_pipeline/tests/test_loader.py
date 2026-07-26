"""Tests for Stage 1: DocumentLoader."""

from pathlib import Path

import pytest

from document_fixtures import write_docx, write_pdf, write_txt
from document_pipeline.core.exceptions import (
  CorruptedDocumentError,
  UnreadableDocumentError,
  UnsupportedFileTypeError,
)
from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.loader import DocumentLoader


def _make_source(
  file_path: Path,
  *,
  document_id: str = "doc-test-001",
  document_format: DocumentFormat = DocumentFormat.UNKNOWN,
) -> DocumentSource:
  metadata = DocumentMetadata(
    document_id=document_id,
    filename=file_path.name,
    format=document_format,
    source_path=str(file_path),
  )
  return DocumentSource(metadata=metadata)


def test_loader_loads_valid_txt(tmp_path: Path, document_loader: DocumentLoader) -> None:
  content = "Privacy Policy\n\nWe collect data.\n"
  file_path = write_txt(tmp_path / "privacy_policy.txt", content)

  loaded = document_loader.process(_make_source(file_path))

  assert loaded.raw_text == file_path.read_bytes().decode("utf-8")
  assert loaded.page_count is None
  assert loaded.metadata.filename == "privacy_policy.txt"
  assert loaded.metadata.format == DocumentFormat.TXT
  assert loaded.extraction_notes == []


def test_loader_loads_valid_pdf(tmp_path: Path, document_loader: DocumentLoader) -> None:
  file_path = write_pdf(
    tmp_path / "privacy_policy.pdf",
    "Privacy Policy Content",
    title="Privacy Policy",
    author="Legal Team",
  )

  loaded = document_loader.process(_make_source(file_path))

  assert "Privacy Policy Content" in loaded.raw_text
  assert loaded.page_count == 1
  assert loaded.metadata.format == DocumentFormat.PDF
  assert loaded.metadata.title == "Privacy Policy"
  assert loaded.metadata.extra.get("author") == "Legal Team"


def test_loader_loads_valid_docx(tmp_path: Path, document_loader: DocumentLoader) -> None:
  paragraphs = ["Section 1", "We collect personal information."]
  file_path = write_docx(
    tmp_path / "privacy_policy.docx",
    paragraphs,
    title="Privacy Policy",
    author="Compliance Team",
  )

  loaded = document_loader.process(_make_source(file_path))

  assert loaded.raw_text == "Section 1\nWe collect personal information."
  assert loaded.page_count is None
  assert loaded.metadata.format == DocumentFormat.DOCX
  assert loaded.metadata.title == "Privacy Policy"
  assert loaded.metadata.extra.get("author") == "Compliance Team"
  assert "creation_date" in loaded.metadata.extra


def test_loader_raises_for_unsupported_extension(
  tmp_path: Path,
  document_loader: DocumentLoader,
) -> None:
  file_path = write_txt(tmp_path / "notes.xyz", "unsupported")

  with pytest.raises(UnsupportedFileTypeError, match="Unsupported file type"):
    document_loader.process(_make_source(file_path))


def test_loader_raises_for_missing_file(document_loader: DocumentLoader) -> None:
  missing_path = Path("does-not-exist.pdf")
  source = _make_source(missing_path)

  with pytest.raises(UnreadableDocumentError, match="Document not found"):
    document_loader.process(source)


def test_loader_raises_for_corrupted_pdf(tmp_path: Path, document_loader: DocumentLoader) -> None:
  file_path = tmp_path / "corrupted.pdf"
  file_path.write_bytes(b"%PDF-1.4\n% corrupted content")

  with pytest.raises(CorruptedDocumentError):
    document_loader.process(_make_source(file_path))


def test_loader_raises_for_corrupted_docx(tmp_path: Path, document_loader: DocumentLoader) -> None:
  file_path = tmp_path / "corrupted.docx"
  file_path.write_bytes(b"PK\x03\x04not-a-valid-docx")

  with pytest.raises(CorruptedDocumentError):
    document_loader.process(_make_source(file_path))


def test_loader_raises_for_unreadable_txt_encoding(
  tmp_path: Path,
  document_loader: DocumentLoader,
) -> None:
  file_path = tmp_path / "binary.txt"
  file_path.write_bytes(b"\xff\xfe\x00\x00")
  source = DocumentSource(
    metadata=DocumentMetadata(
      document_id="doc-binary",
      filename=file_path.name,
      format=DocumentFormat.TXT,
      source_path=str(file_path),
    ),
    encoding="utf-8",
  )

  with pytest.raises(UnreadableDocumentError, match="Failed to decode"):
    document_loader.process(source)


def test_loader_preserves_source_title_when_present(
  tmp_path: Path,
  document_loader: DocumentLoader,
) -> None:
  file_path = write_pdf(tmp_path / "policy.pdf", "Body text", title="Embedded Title")
  metadata = DocumentMetadata(
    document_id="doc-title",
    filename=file_path.name,
    format=DocumentFormat.UNKNOWN,
    title="Provided Title",
    source_path=str(file_path),
  )

  loaded = document_loader.process(DocumentSource(metadata=metadata))

  assert loaded.metadata.title == "Provided Title"


def test_loader_is_deterministic(tmp_path: Path, document_loader: DocumentLoader) -> None:
  file_path = write_txt(tmp_path / "repeatable.txt", "Same content each run.")
  source = _make_source(file_path)

  first = document_loader.process(source)
  second = document_loader.process(source)

  assert first == second
