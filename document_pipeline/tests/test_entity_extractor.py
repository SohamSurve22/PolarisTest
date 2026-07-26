"""Tests for Stage 7: Entity Extractor."""

import pytest

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextDocument, ContextualClause, Reference
from document_pipeline.models.entity import Entity, EntityClause, EntityDocument, EntityType
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, ClassifiedDocument, StructuralRole
from document_pipeline.pipeline.stages.entity_extractor import (
  ActorDetector,
  DocumentDetector,
  EntityExtractor,
  EntityMerger,
  ObjectDetector,
  ReferenceEntityDetector,
  TimeDetector,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_cc(
  text: str,
  *,
  clause_id: str = "S001_C001",
  section_id: str = "S001",
  references: list[Reference] | None = None,
) -> ContextualClause:
  classified = ClassifiedClause(
    clause=Clause(
      clause_id=clause_id,
      section_id=section_id,
      section_title=None,
      document_id="doc-ent-001",
      document_type=DocumentFormat.TXT,
      clause_text=text,
      span=Span(start=0, end=len(text)),
    ),
    role=StructuralRole.STATEMENT,
  )
  return ContextualClause(
    classified_clause=classified,
    detected_references=references or [],
  )


def _make_context_document(clauses: list[ContextualClause]) -> ContextDocument:
  metadata = DocumentMetadata(
    document_id="doc-ent-001",
    filename="test.txt",
    format=DocumentFormat.TXT,
  )
  return ContextDocument(metadata=metadata, contextual_clauses=clauses)


# ===================================================================
# ActorDetector
# ===================================================================

class TestActorDetector:

  def test_detects_data_fiduciary(self) -> None:
    detector = ActorDetector()
    entities = detector.detect("The Data Fiduciary shall process data.")
    assert len(entities) == 1
    assert entities[0].entity_text == "Data Fiduciary"
    assert entities[0].entity_type == EntityType.LEGAL_ACTOR

  def test_detects_board_case_insensitive(self) -> None:
    detector = ActorDetector()
    entities = detector.detect("the board approved")
    assert len(entities) == 1
    assert entities[0].entity_text == "board"
    assert entities[0].entity_type == EntityType.LEGAL_ACTOR

  def test_detects_multiple_actors(self) -> None:
    detector = ActorDetector()
    entities = detector.detect("The Data Fiduciary and the Authority shall agree.")
    assert len(entities) == 2
    types = {e.entity_text.lower() for e in entities}
    assert "data fiduciary" in types
    assert "authority" in types

  def test_no_false_positive_partial_word(self) -> None:
    detector = ActorDetector()
    entities = detector.detect("The courtroom was silent.")
    assert not any(e.entity_text.lower() == "court" for e in entities)

  def test_returns_empty_for_no_actors(self) -> None:
    detector = ActorDetector()
    entities = detector.detect("Nothing here.")
    assert entities == []

  def test_reports_correct_offsets(self) -> None:
    detector = ActorDetector()
    entities = detector.detect("X Data Principal Y")
    assert len(entities) == 1
    assert entities[0].start_offset == 2
    assert entities[0].end_offset == 16

  def test_confidence_and_method(self) -> None:
    detector = ActorDetector()
    entities = detector.detect("The Data Fiduciary")
    assert entities[0].confidence == 0.95
    assert entities[0].detection_method == "actor_dict"


# ===================================================================
# DocumentDetector
# ===================================================================

class TestDocumentDetector:

  def test_detects_dpdp_act(self) -> None:
    detector = DocumentDetector()
    entities = detector.detect("As per the DPDP Act.")
    assert len(entities) == 1
    assert entities[0].entity_text == "DPDP Act"
    assert entities[0].entity_type == EntityType.LEGAL_DOCUMENT

  def test_detects_constitution(self) -> None:
    detector = DocumentDetector()
    entities = detector.detect("Under the Constitution.")
    assert len(entities) == 1
    assert entities[0].entity_text == "Constitution"

  def test_returns_empty_for_no_documents(self) -> None:
    detector = DocumentDetector()
    entities = detector.detect("No legal document here.")
    assert entities == []


# ===================================================================
# ObjectDetector
# ===================================================================

class TestObjectDetector:

  def test_detects_personal_data(self) -> None:
    detector = ObjectDetector()
    entities = detector.detect("Process personal data.")
    assert len(entities) == 1
    assert entities[0].entity_text == "personal data"
    assert entities[0].entity_type == EntityType.LEGAL_OBJECT

  def test_detects_multiple_objects(self) -> None:
    detector = ObjectDetector()
    entities = detector.detect("Consent and notice are required.")
    assert len(entities) == 2
    assert {e.entity_text.lower() for e in entities} == {"consent", "notice"}

  def test_detects_compound_term(self) -> None:
    detector = ObjectDetector()
    entities = detector.detect("Protect sensitive personal data.")
    # Both "sensitive personal data" and "personal data" match; merger deduplicates
    assert len(entities) == 2
    assert entities[0].entity_text == "sensitive personal data"


# ===================================================================
# TimeDetector
# ===================================================================

class TestTimeDetector:

  def test_detects_duration_days(self) -> None:
    detector = TimeDetector()
    entities = detector.detect("30 days.")
    assert len(entities) == 1
    assert entities[0].entity_type == EntityType.TIME
    assert entities[0].entity_text.lower() == "30 days"

  def test_detects_immediately(self) -> None:
    detector = TimeDetector()
    entities = detector.detect("Shall act immediately.")
    assert len(entities) == 1
    assert entities[0].entity_text == "immediately"
    assert entities[0].entity_type == EntityType.TIME

  def test_detects_explicit_date(self) -> None:
    detector = TimeDetector()
    entities = detector.detect("Effective 01/01/2025.")
    assert len(entities) == 1
    assert entities[0].entity_type == EntityType.DATE

  def test_detects_date_named_month(self) -> None:
    detector = TimeDetector()
    entities = detector.detect("Signed on 15 March 2025.")
    assert len(entities) == 1
    assert entities[0].entity_type == EntityType.DATE

  def test_detects_iso_date(self) -> None:
    detector = TimeDetector()
    entities = detector.detect("As of 2025-03-15.")
    assert len(entities) == 1
    assert entities[0].entity_type == EntityType.DATE

  def test_returns_empty_for_no_time(self) -> None:
    detector = TimeDetector()
    entities = detector.detect("No time expression.")
    assert entities == []


# ===================================================================
# ReferenceEntityDetector
# ===================================================================

class TestReferenceEntityDetector:

  def test_converts_references(self) -> None:
    detector = ReferenceEntityDetector()
    refs = [Reference(reference_text="Section 5", reference_type="section", start=10, end=19)]
    entities = detector.detect_from_references(refs)
    assert len(entities) == 1
    assert entities[0].entity_text == "Section 5"
    assert entities[0].entity_type == EntityType.LAW_REFERENCE
    assert entities[0].start_offset == 10
    assert entities[0].end_offset == 19

  def test_returns_empty_for_no_references(self) -> None:
    detector = ReferenceEntityDetector()
    entities = detector.detect_from_references([])
    assert entities == []


# ===================================================================
# EntityMerger
# ===================================================================

class TestEntityMerger:

  def test_merges_non_overlapping(self) -> None:
    merger = EntityMerger()
    e1 = Entity(entity_id="E001", entity_text="Data Fiduciary", entity_type=EntityType.LEGAL_ACTOR, start_offset=4, end_offset=18, confidence=0.95, detection_method="actor_dict")
    e2 = Entity(entity_id="E002", entity_text="consent", entity_type=EntityType.LEGAL_OBJECT, start_offset=25, end_offset=32, confidence=0.95, detection_method="object_dict")
    merged = merger.merge([e1], [e2])
    assert len(merged) == 2

  def test_deduplicates_exact_span(self) -> None:
    merger = EntityMerger()
    e1 = Entity(entity_id="E001", entity_text="personal data", entity_type=EntityType.LEGAL_OBJECT, start_offset=10, end_offset=22, confidence=0.95, detection_method="object_dict")
    e2 = Entity(entity_id="E002", entity_text="personal data", entity_type=EntityType.LEGAL_OBJECT, start_offset=10, end_offset=22, confidence=0.95, detection_method="object_dict")
    merged = merger.merge([e1], [e2])
    assert len(merged) == 1

  def test_longest_wins_overlap(self) -> None:
    merger = EntityMerger()
    short = Entity(entity_id="E001", entity_text="personal data", entity_type=EntityType.LEGAL_OBJECT, start_offset=10, end_offset=22, confidence=0.95, detection_method="object_dict")
    long = Entity(entity_id="E002", entity_text="sensitive personal data", entity_type=EntityType.LEGAL_OBJECT, start_offset=10, end_offset=32, confidence=0.95, detection_method="object_dict")
    merged = merger.merge([short], [long])
    assert len(merged) == 1
    assert merged[0].entity_text == "sensitive personal data"


# ===================================================================
# EntityExtractor (integration)
# ===================================================================

class TestEntityExtractor:

  def test_extracts_multiple_entities(self) -> None:
    cc = _make_cc(
      "The Data Fiduciary shall obtain consent within 30 days.",
    )
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    result = extractor.process(doc)

    assert isinstance(result, EntityDocument)
    assert len(result.entity_clauses) == 1
    ec = result.entity_clauses[0]
    assert len(ec.entities) >= 3
    types = {e.entity_type for e in ec.entities}
    assert EntityType.LEGAL_ACTOR in types
    assert EntityType.LEGAL_OBJECT in types
    assert EntityType.TIME in types

  def test_multiple_entity_types_in_one_clause(self) -> None:
    cc = _make_cc(
      "The Board under the DPDP Act shall protect personal data.",
    )
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    result = extractor.process(doc)
    ec = result.entity_clauses[0]
    types = {e.entity_type for e in ec.entities}
    assert EntityType.LEGAL_ACTOR in types  # Board
    assert EntityType.LEGAL_DOCUMENT in types  # DPDP Act
    assert EntityType.LEGAL_OBJECT in types  # personal data

  def test_entities_from_references(self) -> None:
    refs = [Reference(reference_text="Section 5", reference_type="section", start=23, end=32)]
    cc = _make_cc("As per Section 5.", references=refs)
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    result = extractor.process(doc)
    ec = result.entity_clauses[0]
    law_refs = [e for e in ec.entities if e.entity_type == EntityType.LAW_REFERENCE]
    assert len(law_refs) == 1
    assert law_refs[0].entity_text == "Section 5"

  def test_empty_clause(self) -> None:
    cc = _make_cc("")
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    result = extractor.process(doc)
    assert result.entity_clauses[0].entities == []

  def test_empty_document(self) -> None:
    doc = _make_context_document([])
    extractor = EntityExtractor()

    result = extractor.process(doc)
    assert result.metadata.document_id == "doc-ent-001"
    assert result.entity_clauses == []

  def test_preserves_contextual_clause(self) -> None:
    cc = _make_cc("The Data Fiduciary.", clause_id="S001_C001")
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    result = extractor.process(doc)
    assert result.entity_clauses[0].contextual_clause.classified_clause.clause.clause_id == "S001_C001"

  def test_offset_correctness(self) -> None:
    cc = _make_cc("The Data Fiduciary shall act.")
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    result = extractor.process(doc)
    ec = result.entity_clauses[0]
    for ent in ec.entities:
      assert cc.classified_clause.clause.clause_text[ent.start_offset:ent.end_offset] == ent.entity_text

  def test_confidence_values(self) -> None:
    cc = _make_cc("The Data Fiduciary shall comply.")
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    result = extractor.process(doc)
    for ent in result.entity_clauses[0].entities:
      assert 0.0 <= ent.confidence <= 1.0
      assert ent.detection_method != ""

  def test_idempotent(self) -> None:
    cc = _make_cc("The Data Fiduciary shall obtain consent.")
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    first = extractor.process(doc)
    second = extractor.process(doc)

    assert first == second

  def test_detection_method_present(self) -> None:
    cc = _make_cc("The Court and the Tribunal agree.")
    doc = _make_context_document([cc])
    extractor = EntityExtractor()

    result = extractor.process(doc)
    for ent in result.entity_clauses[0].entities:
      assert ent.detection_method in ("actor_dict", "document_dict", "object_dict", "time_duration", "time_adverb", "time_event", "date_explicit", "date_iso", "reference_detector")
