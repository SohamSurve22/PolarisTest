"""Tests for Stage 2: DocumentCleaner."""

from document_pipeline.models.document import CleanedDocument, LoadedDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.cleaner import DocumentCleaner
from document_pipeline.utils.text_normalization import normalize_document_text


def _make_loaded(raw_text: str) -> LoadedDocument:
  metadata = DocumentMetadata(
    document_id="doc-clean-001",
    filename="contract.pdf",
    format=DocumentFormat.PDF,
  )
  return LoadedDocument(metadata=metadata, raw_text=raw_text)


def test_cleaner_normalizes_mixed_line_endings(document_cleaner: DocumentCleaner) -> None:
  loaded = _make_loaded("Section 1\r\n\r\n1.1 Obligations.\r1.2 Term.")

  cleaned = document_cleaner.process(loaded)

  assert cleaned.cleaned_text == "Section 1\n\n1.1 Obligations.\n1.2 Term."
  assert "Normalized line endings to LF" in cleaned.cleaning_notes


def test_cleaner_replaces_pdf_ligatures(document_cleaner: DocumentCleaner) -> None:
  loaded = _make_loaded("Conﬁdentiality, ofﬁce, aﬀect, ﬃle, and ﬄow.")

  cleaned = document_cleaner.process(loaded)

  assert cleaned.cleaned_text == "Confidentiality, office, affect, ffile, and fflow."
  assert "Replaced PDF ligatures" in cleaned.cleaning_notes[0]


def test_cleaner_collapses_excessive_blank_lines(document_cleaner: DocumentCleaner) -> None:
  loaded = _make_loaded("Section 1\n\n\n\n\nSection 2")

  cleaned = document_cleaner.process(loaded)

  assert cleaned.cleaned_text == "Section 1\n\n\nSection 2"
  assert "Collapsed runs of more than two consecutive blank lines" in cleaned.cleaning_notes


def test_cleaner_trims_trailing_whitespace(document_cleaner: DocumentCleaner) -> None:
  loaded = _make_loaded("  Section 1   \n1.1 Partner duties.  \t")

  cleaned = document_cleaner.process(loaded)

  assert cleaned.cleaned_text == "  Section 1\n1.1 Partner duties."
  assert "Trimmed trailing whitespace on each line" in cleaned.cleaning_notes


def test_cleaner_is_idempotent(document_cleaner: DocumentCleaner) -> None:
  loaded = _make_loaded("Section 1\r\n\r\n1.1 Conﬁdentiality.   \n\n\n\n1.2 Term.")

  first = document_cleaner.process(loaded)
  second = document_cleaner.process(
    LoadedDocument(
      metadata=loaded.metadata,
      raw_text=first.cleaned_text,
    ),
  )

  assert second.cleaned_text == first.cleaned_text
  assert second.cleaning_notes == []


def test_cleaner_leaves_already_clean_document_unchanged(
  document_cleaner: DocumentCleaner,
) -> None:
  text = (
    "ARTICLE I\n\n"
    "1.1 The Partner shall comply with 42 U.S.C. § 1983.\n\n"
    "1.2 Confidential information must remain protected."
  )
  loaded = _make_loaded(text)

  cleaned = document_cleaner.process(loaded)

  assert cleaned.cleaned_text == text
  assert cleaned.cleaning_notes == []
  assert cleaned.metadata == loaded.metadata


def test_cleaner_preserves_legal_references_and_capitalization(
  document_cleaner: DocumentCleaner,
) -> None:
  loaded = _make_loaded(
    "See 15 U.S.C. § 78j(b) and EU Reg. (GDPR) Art. 6(1)(f).\n"
    "PARTNER shall indemnify COMPANY."
  )

  cleaned = document_cleaner.process(loaded)

  assert "15 U.S.C. § 78j(b)" in cleaned.cleaned_text
  assert "PARTNER shall indemnify COMPANY." in cleaned.cleaned_text
  assert cleaned.cleaned_text == loaded.raw_text


def test_cleaner_returns_cleaned_document(document_cleaner: DocumentCleaner) -> None:
  cleaned = document_cleaner.process(_make_loaded("Section 1"))

  assert isinstance(cleaned, CleanedDocument)


def test_normalize_document_text_twice_is_idempotent() -> None:
  raw = "Line one\r\n\n\n\nLine two with ﬁ ligature.   "

  once, once_notes = normalize_document_text(raw)
  twice, twice_notes = normalize_document_text(once)

  assert twice == once
  assert twice_notes == []
  assert once_notes
