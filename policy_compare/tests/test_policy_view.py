from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole

from policy_compare.policy_view import policy_view_graph


def _clause(clause_id: str, section_id: str, title: str | None, text: str) -> Clause:
  return Clause(
    clause_id=clause_id,
    section_id=section_id,
    section_title=title,
    document_id="DOC_x",
    document_type=DocumentFormat.TXT,
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )


def _entity_clause(clause: Clause) -> EntityClause:
  classified = ClassifiedClause(
    clause=clause,
    role=StructuralRole.STATEMENT,
    confidence=1.0,
    classification_reason=[],
  )
  contextual = ContextualClause(classified_clause=classified)
  return EntityClause(contextual_clause=contextual, entities=[])


def test_untitled_section_is_introduction() -> None:
  document = EntityDocument(
    metadata=DocumentMetadata(
      document_id="DOC_x",
      filename="policy.txt",
      format=DocumentFormat.TXT,
      title="Acme Policy",
    ),
    entity_clauses=[
      _entity_clause(_clause("S001_C001", "S001", None, "Welcome to Acme.")),
      _entity_clause(_clause("S002_C001", "S002", "Your rights", "You may delete data.")),
    ],
  )
  graph = policy_view_graph(document)
  titles = {node.title for node in graph.nodes if node.kind == "section"}
  assert titles == {"Introduction", "Your rights"}
  assert any(node.kind == "document" and node.title == "Acme Policy" for node in graph.nodes)
  assert all(node.kind != "law_chunk" for node in graph.nodes)
