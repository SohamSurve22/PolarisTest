"""Tests for Stage 5: DocumentUnderstanding."""

import pytest

from document_pipeline.models.clause import Clause, SegmentedDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassificationResult, StructuralRole
from document_pipeline.pipeline.stages.document_understanding import (
  DocumentUnderstanding,
  heuristic_classify,
)


def _make_clause(
  text: str,
  *,
  section_title: str | None = None,
  clause_id: str = "S001_C001",
  document_id: str = "doc-und-001",
) -> Clause:
  return Clause(
    clause_id=clause_id,
    section_id="S001",
    section_title=section_title,
    document_id=document_id,
    document_type=DocumentFormat.TXT,
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )


def _make_segmented(clauses: list[Clause]) -> SegmentedDocument:
  metadata = DocumentMetadata(
    document_id="doc-und-001",
    filename="test.txt",
    format=DocumentFormat.TXT,
  )
  return SegmentedDocument(metadata=metadata, clauses=clauses)


class TestHeuristicClassify:
  """Unit tests for the standalone heuristic_classify function."""

  def _assert(
    self,
    clause: Clause,
    expected_role: StructuralRole,
    *,
    has_reason: bool = True,
  ) -> None:
    result = heuristic_classify(clause)
    assert isinstance(result, ClassificationResult)
    assert result.role == expected_role
    assert 0.0 <= result.confidence <= 1.0
    if has_reason:
      assert len(result.classification_reason) >= 1

  def test_heading_matches_section_title(self) -> None:
    self._assert(
      _make_clause("South Korea", section_title="South Korea"),
      StructuralRole.HEADING,
    )

  def test_heading_short_title_case(self) -> None:
    self._assert(_make_clause("United States"), StructuralRole.HEADING)

  def test_heading_single_word(self) -> None:
    self._assert(_make_clause("Turkey"), StructuralRole.HEADING)

  def test_heading_multi_word_no_verb(self) -> None:
    self._assert(_make_clause("Data Processing Activities"), StructuralRole.HEADING)

  def test_statement_with_shall(self) -> None:
    self._assert(
      _make_clause("The Partner shall maintain confidentiality."),
      StructuralRole.STATEMENT,
    )

  def test_statement_with_may(self) -> None:
    self._assert(
      _make_clause("We may retain your data for legal purposes."),
      StructuralRole.STATEMENT,
    )

  def test_statement_with_must(self) -> None:
    self._assert(
      _make_clause("You must provide accurate information."),
      StructuralRole.STATEMENT,
    )

  def test_statement_longer_text_no_verb(self) -> None:
    self._assert(
      _make_clause("Any notice under this Agreement shall be in writing."),
      StructuralRole.STATEMENT,
    )

  def test_list_item_bullet_dash(self) -> None:
    self._assert(_make_clause("- Phone Number"), StructuralRole.LIST_ITEM)

  def test_list_item_bullet_asterisk(self) -> None:
    self._assert(_make_clause("* Email Address"), StructuralRole.LIST_ITEM)

  def test_list_item_bullet_unicode(self) -> None:
    self._assert(
      _make_clause("\u2022 Email Address"),
      StructuralRole.LIST_ITEM,
    )

  def test_list_item_numbered(self) -> None:
    self._assert(_make_clause("1. Provide notice."), StructuralRole.LIST_ITEM)

  def test_list_item_numbered_paren(self) -> None:
    self._assert(_make_clause("2) Maintain records."), StructuralRole.LIST_ITEM)

  def test_list_item_lettered(self) -> None:
    self._assert(
      _make_clause("(a) Sub-clause item."),
      StructuralRole.LIST_ITEM,
    )

  def test_unknown_empty_text(self) -> None:
    self._assert(_make_clause(""), StructuralRole.UNKNOWN, has_reason=True)

  def test_unknown_short_no_verb_lowercase(self) -> None:
    self._assert(
      _make_clause("some random text"),
      StructuralRole.UNKNOWN,
    )

  def test_classification_reason_populated(self) -> None:
    result = heuristic_classify(
      _make_clause("South Korea", section_title="South Korea"),
    )
    assert "short_text" in result.classification_reason
    assert "matches_section_title" in result.classification_reason
    assert "title_case" in result.classification_reason

  def test_confidence_default_is_one(self) -> None:
    result = heuristic_classify(_make_clause(""))
    assert result.confidence == 1.0


class TestDocumentUnderstandingStage:
  """Integration tests for the DocumentUnderstanding pipeline stage."""

  def test_returns_classified_document(self) -> None:
    clauses = [
      _make_clause("South Korea", section_title="South Korea", clause_id="S001_C001"),
      _make_clause("The Company shall process data.", clause_id="S001_C002"),
      _make_clause("- Email Address", clause_id="S001_C003"),
    ]
    segmented = _make_segmented(clauses)
    stage = DocumentUnderstanding()

    result = stage.process(segmented)

    assert len(result.clauses) == 3
    assert result.metadata.document_id == "doc-und-001"
    assert [c.role for c in result.clauses] == [
      StructuralRole.HEADING,
      StructuralRole.STATEMENT,
      StructuralRole.LIST_ITEM,
    ]

  def test_confidence_and_reason_on_every_clause(self) -> None:
    clause = _make_clause("Data Collection", clause_id="S001_C001")
    segmented = _make_segmented([clause])
    stage = DocumentUnderstanding()

    result = stage.process(segmented)

    classified = result.clauses[0]
    assert 0.0 <= classified.confidence <= 1.0
    assert isinstance(classified.classification_reason, list)
    assert len(classified.classification_reason) >= 1

  def test_preserves_original_clause_data(self) -> None:
    clause = _make_clause("Confidential Information", clause_id="S001_C001")
    segmented = _make_segmented([clause])
    stage = DocumentUnderstanding()

    result = stage.process(segmented)

    classified = result.clauses[0]
    assert classified.clause.clause_id == "S001_C001"
    assert classified.clause.clause_text == "Confidential Information"

  def test_injectable_custom_classifier(self) -> None:
    def always_unknown(_clause: Clause) -> ClassificationResult:
      return ClassificationResult(
        role=StructuralRole.UNKNOWN,
        confidence=0.5,
        classification_reason=["custom"],
      )

    clause = _make_clause("Any text")
    segmented = _make_segmented([clause])
    stage = DocumentUnderstanding(classifier=always_unknown)

    result = stage.process(segmented)

    cc = result.clauses[0]
    assert cc.role == StructuralRole.UNKNOWN
    assert cc.confidence == 0.5
    assert cc.classification_reason == ["custom"]

  def test_idempotent(self) -> None:
    clauses = [
      _make_clause("Turkey", clause_id="S001_C001"),
      _make_clause("We collect information.", clause_id="S001_C002"),
    ]
    segmented = _make_segmented(clauses)
    stage = DocumentUnderstanding()

    first = stage.process(segmented)
    second = stage.process(segmented)

    assert first == second

  def test_parser_models_untouched(self) -> None:
    original = _make_clause("Turkey", clause_id="S001_C001")
    segmented = _make_segmented([original])
    stage = DocumentUnderstanding()
    stage.process(segmented)

    assert original.clause_id == "S001_C001"
    assert original.clause_text == "Turkey"
