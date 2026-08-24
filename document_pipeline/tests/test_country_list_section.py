"""Regression tests for the country-list-as-one-section behaviour.

A vertical list of countries (one name per line, separated by blank lines) must
not be split into a separate section per country.  When such a list follows a
real section heading it is folded into that enclosing section (inheriting its
title, e.g. "Region Specific Information"); only a list at the very top of the
document keeps its first item as the section title.
"""

from document_pipeline.models.document import CleanedDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.section_extractor import SectionExtractor
from document_pipeline.sectioning.heading_detector import HeadingDetector


def _make_cleaned(cleaned_text: str) -> CleanedDocument:
  metadata = DocumentMetadata(
    document_id="doc-country-001",
    filename="policy.txt",
    format=DocumentFormat.TXT,
  )
  return CleanedDocument(metadata=metadata, cleaned_text=cleaned_text)


def test_country_list_under_heading_is_one_section(section_extractor: SectionExtractor) -> None:
  text = (
    "1. Overview\n\n"
    "This policy covers the following jurisdictions.\n\n"
    "Applicable Countries\n\n"
    "United States\n\n"
    "United Kingdom\n\n"
    "France\n\n"
    "Germany\n\n"
    "This policy applies to all the above.\n\n"
    "Data Collection\n\n"
    "We collect personal data.\n"
  )
  sectioned = section_extractor.process(_make_cleaned(text))

  titles = [s.title for s in sectioned.sections if s.title]
  # The country list is folded into the enclosing "1. Overview" section and is
  # NOT given its own section (neither titled "Applicable Countries" nor a
  # country name).
  assert "Applicable Countries" not in titles
  assert "Data Collection" in titles
  assert "United States" not in titles
  assert "United Kingdom" not in titles
  assert "France" not in titles

  # All countries must appear as body text of the enclosing section.
  overview = next(s for s in sectioned.sections if s.title == "1. Overview")
  assert "Applicable Countries" in overview.text
  assert "United States" in overview.text
  assert "Germany" in overview.text


def test_country_list_at_top_is_single_section(section_extractor: SectionExtractor) -> None:
  text = "\nUnited States\n\nUnited Kingdom\n\nFrance\n\n"
  sectioned = section_extractor.process(_make_cleaned(text))

  titled = [s for s in sectioned.sections if s.title]
  assert len(titled) == 1
  assert titled[0].title == "United States"
  assert "United Kingdom" in titled[0].text
  assert "France" in titled[0].text


def test_real_headings_with_body_are_not_merged(section_extractor: SectionExtractor) -> None:
  text = (
    "\nQuestion One\n\nAnswer one.\n\n"
    "Question Two\n\nAnswer two.\n"
  )
  sectioned = section_extractor.process(_make_cleaned(text))

  titles = [s.title for s in sectioned.sections if s.title]
  assert titles == ["Question One", "Question Two"]


def test_heading_detector_collapses_country_list_items() -> None:
  detector = HeadingDetector()
  text = "\nApplicable Countries\n\nUnited States\n\nUnited Kingdom\n\nFrance\n\n"
  headings = detector.detect(text)

  # The list header is retained; the country items are collapsed into its body.
  assert len(headings) == 1
  assert headings[0].title == "Applicable Countries"
