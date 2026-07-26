"""Tests for Stage 6: Context Builder."""

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextDocument, ContextualClause, Reference
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, ClassifiedDocument, StructuralRole
from document_pipeline.pipeline.stages.context_builder import (
  ContextBuilder,
  NeighborResolver,
  ReferenceDetector,
  SectionContextBuilder,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_classified(
  text: str,
  *,
  clause_id: str = "S001_C001",
  section_id: str = "S001",
  section_title: str | None = None,
  document_id: str = "doc-ctx-001",
) -> ClassifiedClause:
  return ClassifiedClause(
    clause=Clause(
      clause_id=clause_id,
      section_id=section_id,
      section_title=section_title,
      document_id=document_id,
      document_type=DocumentFormat.TXT,
      clause_text=text,
      span=Span(start=0, end=len(text)),
    ),
    role=StructuralRole.STATEMENT,
  )


def _build_classified_document(clauses: list[ClassifiedClause]) -> ClassifiedDocument:
  metadata = DocumentMetadata(
    document_id="doc-ctx-001",
    filename="test.txt",
    format=DocumentFormat.TXT,
  )
  return ClassifiedDocument(metadata=metadata, clauses=clauses)


# ===================================================================
# ReferenceDetector
# ===================================================================

class TestReferenceDetector:

  def test_detects_section_reference(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("As per Section 5, the obligations apply.")
    assert len(refs) == 1
    assert refs[0].reference_text == "Section 5"
    assert refs[0].reference_type == "section"
    assert not refs[0].resolved

  def test_detects_subsection_reference(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("See subsection (3) for details.")
    assert len(refs) == 1
    assert refs[0].reference_text == "subsection (3)"
    assert refs[0].reference_type == "subsection"

  def test_detects_rule_reference(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("As per Rule 8.")
    assert len(refs) == 1
    assert refs[0].reference_text == "Rule 8"
    assert refs[0].reference_type == "rule"

  def test_detects_article_reference(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("Article 21 states the following.")
    assert len(refs) == 1
    assert refs[0].reference_text == "Article 21"
    assert refs[0].reference_type == "article"

  def test_detects_chapter_reference(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("See Chapter IV.")
    assert len(refs) == 1
    assert refs[0].reference_text == "Chapter IV"
    assert refs[0].reference_type == "chapter"

  def test_detects_schedule_reference(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("Schedule I lists the forms.")
    assert len(refs) == 1
    assert refs[0].reference_text == "Schedule I"
    assert refs[0].reference_type == "schedule"

  def test_detects_clause_reference(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("As defined in Clause 2.")
    assert len(refs) == 1
    assert refs[0].reference_text == "Clause 2"
    assert refs[0].reference_type == "clause"

  def test_detects_regulation_reference(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("Regulation 7 applies.")
    assert len(refs) == 1
    assert refs[0].reference_text == "Regulation 7"
    assert refs[0].reference_type == "regulation"

  def test_detects_this_act(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("Under this Act, the Board shall...")
    assert len(refs) == 1
    assert refs[0].reference_text == "this Act"
    assert refs[0].reference_type == "act"

  def test_detects_that_act(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("As defined in that Act.")
    assert len(refs) == 1
    assert refs[0].reference_text == "that Act"
    assert refs[0].reference_type == "act"

  def test_detects_the_rules(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("Comply with the Rules.")
    assert len(refs) == 1
    assert refs[0].reference_text == "the Rules"
    assert refs[0].reference_type == "rules"

  def test_detects_the_code(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("As per the Code.")
    assert len(refs) == 1
    assert refs[0].reference_text == "the Code"
    assert refs[0].reference_type == "code"

  def test_detects_multiple_references(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect(
      "Under Section 5 and Rule 8, this Act applies.",
    )
    assert len(refs) == 3
    types = [r.reference_type for r in refs]
    assert types == ["section", "rule", "act"]

  def test_returns_empty_for_no_references(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("The party shall maintain confidentiality.")
    assert refs == []

  def test_reports_correct_character_offsets(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("X Section 5 Y")
    assert len(refs) == 1
    assert refs[0].start == 2
    assert refs[0].end == 11
    assert refs[0].reference_text == "Section 5"

  def test_no_duplicate_overlapping_matches(self) -> None:
    detector = ReferenceDetector()
    refs = detector.detect("Section 5 section 5")
    assert len(refs) == 2


# ===================================================================
# NeighborResolver
# ===================================================================

class TestNeighborResolver:

  def test_single_clause_has_no_neighbors(self) -> None:
    resolver = NeighborResolver()
    clauses = [_make_classified("Only clause.", clause_id="S001_C001")]
    result = resolver.resolve(clauses)

    info = result["S001_C001"]
    assert info.previous_clause_id is None
    assert info.next_clause_id is None
    assert info.neighbor_clause_ids == []

  def test_two_clauses_linked_correctly(self) -> None:
    resolver = NeighborResolver()
    clauses = [
      _make_classified("First.", clause_id="S001_C001"),
      _make_classified("Second.", clause_id="S001_C002"),
    ]
    result = resolver.resolve(clauses)

    assert result["S001_C001"].previous_clause_id is None
    assert result["S001_C001"].next_clause_id == "S001_C002"
    assert result["S001_C001"].neighbor_clause_ids == ["S001_C002"]

    assert result["S001_C002"].previous_clause_id == "S001_C001"
    assert result["S001_C002"].next_clause_id is None
    assert result["S001_C002"].neighbor_clause_ids == ["S001_C001"]

  def test_three_clauses_chain(self) -> None:
    resolver = NeighborResolver()
    clauses = [
      _make_classified("A.", clause_id="C001"),
      _make_classified("B.", clause_id="C002"),
      _make_classified("C.", clause_id="C003"),
    ]
    result = resolver.resolve(clauses)

    assert result["C001"].neighbor_clause_ids == ["C002"]
    assert result["C002"].neighbor_clause_ids == ["C001", "C003"]
    assert result["C003"].neighbor_clause_ids == ["C002"]

  def test_respects_document_order(self) -> None:
    resolver = NeighborResolver()
    clauses = [
      _make_classified("First.", clause_id="C002"),
      _make_classified("Second.", clause_id="C001"),
    ]
    result = resolver.resolve(clauses)

    assert result["C002"].next_clause_id == "C001"
    assert result["C001"].previous_clause_id == "C002"

  def test_empty_clause_list(self) -> None:
    resolver = NeighborResolver()
    result = resolver.resolve([])
    assert result == {}


# ===================================================================
# SectionContextBuilder
# ===================================================================

class TestSectionContextBuilder:

  def test_single_section_first_and_last(self) -> None:
    builder = SectionContextBuilder()
    clauses = [
      _make_classified("C1.", section_id="S001", clause_id="S001_C001"),
      _make_classified("C2.", section_id="S001", clause_id="S001_C002"),
    ]
    result = builder.build(clauses)

    assert result["S001_C001"].position == 0
    assert result["S001_C001"].is_first is True
    assert result["S001_C001"].is_last is False

    assert result["S001_C002"].position == 1
    assert result["S001_C002"].is_first is False
    assert result["S001_C002"].is_last is True

  def test_multiple_sections(self) -> None:
    builder = SectionContextBuilder()
    clauses = [
      _make_classified("S1C1.", section_id="S001", clause_id="S001_C001"),
      _make_classified("S1C2.", section_id="S001", clause_id="S001_C002"),
      _make_classified("S2C1.", section_id="S002", clause_id="S002_C001"),
      _make_classified("S2C2.", section_id="S002", clause_id="S002_C002"),
      _make_classified("S2C3.", section_id="S002", clause_id="S002_C003"),
    ]
    result = builder.build(clauses)

    assert result["S001_C001"].position == 0
    assert result["S001_C001"].is_first is True
    assert result["S001_C001"].is_last is False

    assert result["S001_C002"].position == 1
    assert result["S001_C002"].is_first is False
    assert result["S001_C002"].is_last is True

    assert result["S002_C001"].position == 0
    assert result["S002_C001"].is_first is True
    assert result["S002_C001"].is_last is False

    assert result["S002_C003"].position == 2
    assert result["S002_C003"].is_first is False
    assert result["S002_C003"].is_last is True

  def test_empty_clause_list(self) -> None:
    builder = SectionContextBuilder()
    result = builder.build([])
    assert result == {}

  def test_single_clause_section(self) -> None:
    builder = SectionContextBuilder()
    clauses = [
      _make_classified("Only.", section_id="S001", clause_id="S001_C001"),
    ]
    result = builder.build(clauses)

    assert result["S001_C001"].position == 0
    assert result["S001_C001"].is_first is True
    assert result["S001_C001"].is_last is True


# ===================================================================
# ContextBuilder (integration)
# ===================================================================

class TestContextBuilder:

  def test_builds_context_document(self) -> None:
    clauses = [
      _make_classified("First clause.", section_id="S001", clause_id="S001_C001"),
      _make_classified("Second clause.", section_id="S001", clause_id="S001_C002"),
    ]
    doc = _build_classified_document(clauses)
    builder = ContextBuilder()

    result = builder.process(doc)

    assert isinstance(result, ContextDocument)
    assert result.metadata.document_id == "doc-ctx-001"
    assert len(result.contextual_clauses) == 2

  def test_neighbor_linkage(self) -> None:
    clauses = [
      _make_classified("C1.", section_id="S001", clause_id="S001_C001"),
      _make_classified("C2.", section_id="S001", clause_id="S001_C002"),
      _make_classified("C3.", section_id="S001", clause_id="S001_C003"),
    ]
    doc = _build_classified_document(clauses)
    builder = ContextBuilder()
    result = builder.process(doc)

    cc = result.contextual_clauses

    assert cc[0].previous_clause_id is None
    assert cc[0].next_clause_id == "S001_C002"
    assert cc[0].neighbor_clause_ids == ["S001_C002"]

    assert cc[1].previous_clause_id == "S001_C001"
    assert cc[1].next_clause_id == "S001_C003"
    assert cc[1].neighbor_clause_ids == ["S001_C001", "S001_C003"]

    assert cc[2].previous_clause_id == "S001_C002"
    assert cc[2].next_clause_id is None
    assert cc[2].neighbor_clause_ids == ["S001_C002"]

  def test_section_bounds(self) -> None:
    clauses = [
      _make_classified("S1C1.", section_id="S001", clause_id="S001_C001"),
      _make_classified("S1C2.", section_id="S001", clause_id="S001_C002"),
      _make_classified("S2C1.", section_id="S002", clause_id="S002_C001"),
    ]
    doc = _build_classified_document(clauses)
    builder = ContextBuilder()
    result = builder.process(doc)

    assert result.contextual_clauses[0].is_first_in_section is True
    assert result.contextual_clauses[0].is_last_in_section is False
    assert result.contextual_clauses[0].section_position == 0

    assert result.contextual_clauses[1].is_first_in_section is False
    assert result.contextual_clauses[1].is_last_in_section is True
    assert result.contextual_clauses[1].section_position == 1

    assert result.contextual_clauses[2].is_first_in_section is True
    assert result.contextual_clauses[2].is_last_in_section is True
    assert result.contextual_clauses[2].section_position == 0

  def test_detects_references(self) -> None:
    clauses = [
      _make_classified("As per Section 5.", section_id="S001", clause_id="S001_C001"),
      _make_classified("No references here.", section_id="S001", clause_id="S001_C002"),
    ]
    doc = _build_classified_document(clauses)
    builder = ContextBuilder()
    result = builder.process(doc)

    assert len(result.contextual_clauses[0].detected_references) == 1
    assert result.contextual_clauses[0].detected_references[0].reference_text == "Section 5"

    assert result.contextual_clauses[1].detected_references == []

  def test_empty_document(self) -> None:
    doc = _build_classified_document([])
    builder = ContextBuilder()
    result = builder.process(doc)

    assert result.metadata.document_id == "doc-ctx-001"
    assert result.contextual_clauses == []

  def test_preserves_classified_clause(self) -> None:
    clauses = [
      _make_classified("Important.", section_id="S001", clause_id="S001_C001"),
    ]
    doc = _build_classified_document(clauses)
    builder = ContextBuilder()
    result = builder.process(doc)

    cc = result.contextual_clauses[0]
    assert cc.classified_clause.clause.clause_text == "Important."
    assert cc.classified_clause.role == StructuralRole.STATEMENT

  def test_injectable_components(self) -> None:
    from document_pipeline.pipeline.stages.context_builder import (
      NeighborResolver,
      ReferenceDetector,
      SectionContextBuilder,
    )

    builder = ContextBuilder(
      reference_detector=ReferenceDetector(),
      neighbor_resolver=NeighborResolver(),
      section_context_builder=SectionContextBuilder(),
    )

    clauses = [_make_classified("Text.", clause_id="S001_C001")]
    doc = _build_classified_document(clauses)
    result = builder.process(doc)

    assert len(result.contextual_clauses) == 1

  def test_idempotent(self) -> None:
    clauses = [
      _make_classified("C1.", section_id="S001", clause_id="S001_C001"),
      _make_classified("C2.", section_id="S001", clause_id="S001_C002"),
    ]
    doc = _build_classified_document(clauses)
    builder = ContextBuilder()

    first = builder.process(doc)
    second = builder.process(doc)

    assert first == second
