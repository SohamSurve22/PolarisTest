import json
from pathlib import Path

import pytest

from document_pipeline.models.document import CleanedDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.section_extractor import SectionExtractor
from document_pipeline.sectioning.heading_detector import HeadingDetector

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "policies"
_POLICY_FILES = sorted(_FIXTURE_DIR.glob("*.txt"))


def _expected_headings(policy_path: Path) -> list[str]:
  sidecar = policy_path.with_suffix(".expected.json")
  payload = json.loads(sidecar.read_text(encoding="utf-8"))
  return list(payload["headings"])


def _cleaned(text: str, filename: str) -> CleanedDocument:
  return CleanedDocument(
    metadata=DocumentMetadata(
      document_id="doc-fixture-001",
      filename=filename,
      format=DocumentFormat.TXT,
    ),
    cleaned_text=text,
  )


@pytest.mark.parametrize("policy_path", _POLICY_FILES, ids=lambda path: path.stem)
def test_heading_detector_matches_gold_titles(policy_path: Path) -> None:
  text = policy_path.read_text(encoding="utf-8")
  headings = HeadingDetector().detect(text)
  assert [heading.title for heading in headings] == _expected_headings(policy_path)


@pytest.mark.parametrize("policy_path", _POLICY_FILES, ids=lambda path: path.stem)
def test_section_extractor_titles_match_gold(policy_path: Path) -> None:
  text = policy_path.read_text(encoding="utf-8")
  sectioned = SectionExtractor().process(_cleaned(text, policy_path.name))
  titled = [section.title for section in sectioned.sections if section.title]
  assert titled == _expected_headings(policy_path)
