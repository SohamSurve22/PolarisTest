"""Tests for Stage 3: SectionExtractor."""

from document_pipeline.models.document import CleanedDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.section_extractor import SectionExtractor
from document_pipeline.sectioning.heading_detector import HeadingDetector
from document_pipeline.sectioning.types import HeadingStyle


def _make_cleaned(cleaned_text: str) -> CleanedDocument:
  metadata = DocumentMetadata(
    document_id="doc-section-001",
    filename="policy.txt",
    format=DocumentFormat.TXT,
  )
  return CleanedDocument(metadata=metadata, cleaned_text=cleaned_text)


def _join_sections(sectioned) -> str:
  return "".join(section.text for section in sectioned.sections)


def test_extractor_detects_numbered_headings(section_extractor: SectionExtractor) -> None:
  text = "3. Data Retention\n\nWe retain data for 30 days.\n"
  sectioned = section_extractor.process(_make_cleaned(text))

  assert len(sectioned.sections) == 1
  section = sectioned.sections[0]
  assert section.section_id == "S001"
  assert section.title == "3. Data Retention"
  assert section.level == 1
  assert section.text == text
  assert section.span.start == 0
  assert section.span.end == len(text)


def test_extractor_detects_roman_numeral_headings(section_extractor: SectionExtractor) -> None:
  text = "IV. Liability\n\nThe Partner is liable.\n"
  sectioned = section_extractor.process(_make_cleaned(text))

  assert sectioned.sections[0].title == "IV. Liability"
  assert sectioned.sections[0].level == 1


def test_extractor_detects_markdown_headings(section_extractor: SectionExtractor) -> None:
  text = "## Privacy Policy\n\nWe value privacy.\n\n### Data Use\n\nDetails here.\n"
  sectioned = section_extractor.process(_make_cleaned(text))

  assert len(sectioned.sections) == 2
  assert sectioned.sections[0].title == "Privacy Policy"
  assert sectioned.sections[0].level == 2
  assert sectioned.sections[1].title == "Data Use"
  assert sectioned.sections[1].level == 3
  assert sectioned.sections[1].parent_section_id == sectioned.sections[0].section_id


def test_extractor_detects_uppercase_headings(section_extractor: SectionExtractor) -> None:
  text = "ARTICLE I\n\nDefinitions apply.\n"
  sectioned = section_extractor.process(_make_cleaned(text))

  assert sectioned.sections[0].title == "ARTICLE I"
  assert sectioned.sections[0].level == 1


def test_extractor_detects_colon_headings(section_extractor: SectionExtractor) -> None:
  text = "Data Retention:\n\nWe retain logs for 90 days.\n"
  sectioned = section_extractor.process(_make_cleaned(text))

  assert sectioned.sections[0].title == "Data Retention"
  assert sectioned.sections[0].text.startswith("Data Retention:\n")


def test_extractor_returns_single_section_without_headings(
  section_extractor: SectionExtractor,
) -> None:
  text = "This policy explains how we process personal data without formal headings."
  sectioned = section_extractor.process(_make_cleaned(text))

  assert len(sectioned.sections) == 1
  assert sectioned.sections[0].section_id == "S001"
  assert sectioned.sections[0].title is None
  assert sectioned.sections[0].text == text


def test_extractor_handles_nested_headings(section_extractor: SectionExtractor) -> None:
  text = (
    "1. Main Topic\n\n"
    "Main content.\n\n"
    "1.1 Sub Topic\n\n"
    "Sub content.\n\n"
    "2. Next Topic\n\n"
    "More content."
  )
  sectioned = section_extractor.process(_make_cleaned(text))

  assert [section.section_id for section in sectioned.sections] == ["S001", "S002", "S003"]
  assert sectioned.sections[0].title == "1. Main Topic"
  assert sectioned.sections[1].title == "1.1 Sub Topic"
  assert sectioned.sections[1].parent_section_id == "S001"
  assert sectioned.sections[1].level == 2
  assert sectioned.sections[2].title == "2. Next Topic"
  assert sectioned.sections[2].parent_section_id is None


def test_extractor_preserves_original_text(section_extractor: SectionExtractor) -> None:
  text = (
    "Preamble paragraph.\n\n"
    "1. Scope\n\n"
    "Applies to all users.\n\n"
  )
  sectioned = section_extractor.process(_make_cleaned(text))

  assert sectioned.full_text == text
  assert _join_sections(sectioned) == text


def test_extractor_uses_correct_character_offsets(section_extractor: SectionExtractor) -> None:
  text = "Intro\n\n1. Scope\n\nBody text."
  sectioned = section_extractor.process(_make_cleaned(text))

  for section in sectioned.sections:
    assert section.text == text[section.span.start : section.span.end]
    assert section.span.end > section.span.start


def test_heading_detector_identifies_styles() -> None:
  detector = HeadingDetector()
  text = (
    "## Markdown\n\n"
    "3. Numbered\n\n"
    "IV. Roman\n\n"
    "ARTICLE V\n\n"
    "Scope:\n\n"
    "Standalone Heading\n\n"
    "Body text."
  )
  headings = detector.detect(text)

  assert [heading.heading_style for heading in headings] == [
    HeadingStyle.MARKDOWN,
    HeadingStyle.NUMBERED,
    HeadingStyle.ROMAN,
    HeadingStyle.UPPERCASE,
    HeadingStyle.COLON,
    HeadingStyle.STANDALONE,
  ]


def test_heading_detector_reports_character_offsets() -> None:
  text = "Preamble\n\n1. Scope\n\nBody."
  headings = detector.detect(text) if (detector := HeadingDetector()) else []

  assert headings[0].start_char == text.index("1. Scope")
  assert text[headings[0].start_char :].startswith("1. Scope")
