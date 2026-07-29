"""Tests for graph prompt serialization."""

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause, Reference
from document_pipeline.models.entity import Entity, EntityClause, EntityDocument, EntityType
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole

from graph_builder.graph_prompt import (
  build_system_prompt,
  build_user_prompt,
  serialize_entity_document,
)


def _entity_document() -> EntityDocument:
  metadata = DocumentMetadata(
    document_id="DOC_prompt",
    filename="spdi.txt",
    format=DocumentFormat.TXT,
    title="SPDI Rules",
  )
  clause = Clause(
    clause_id="S001_C001",
    document_id="DOC_prompt",
    document_type=DocumentFormat.TXT,
    section_id="S001",
    section_title="Definitions",
    clause_text="Sensitive personal data means such personal information as may be prescribed.",
    span=Span(start=0, end=80),
  )
  classified = ClassifiedClause(
    clause=clause,
    role=StructuralRole.STATEMENT,
    confidence=0.95,
  )
  contextual = ContextualClause(
    classified_clause=classified,
    detected_references=[
      Reference(reference_text="Section 43A", reference_type="section"),
    ],
  )
  entity_clause = EntityClause(
    contextual_clause=contextual,
    entities=[
      Entity(
        entity_id="E001",
        entity_text="Sensitive personal data",
        entity_type=EntityType.LEGAL_OBJECT,
      ),
    ],
  )
  return EntityDocument(metadata=metadata, entity_clauses=[entity_clause])


class TestGraphPrompt:
  def test_system_prompt_lists_allowed_labels(self) -> None:
    prompt = build_system_prompt()
    assert "LawVersion" in prompt
    assert "HAS_SECTION" in prompt
    assert "Return ONLY valid JSON" in prompt

  def test_serialize_entity_document_produces_structured_json(self) -> None:
    payload = serialize_entity_document(_entity_document())
    assert "DOC_prompt" in payload
    assert "Sensitive personal data" in payload
    assert "S001_C001" in payload
    assert "Section 43A" in payload

  def test_user_prompt_wraps_structured_json(self) -> None:
    prompt = build_user_prompt(_entity_document())
    assert "Convert the following structured legal document JSON" in prompt
    assert "DOC_prompt" in prompt
