from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.section import Section, SectionedDocument
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
  intro = next(node for node in graph.nodes if node.title == "Introduction")
  assert intro.extra.get("parent_section_id") == ""
  assert any(node.kind == "document" and node.title == "Acme Policy" for node in graph.nodes)
  assert all(node.kind != "law_chunk" for node in graph.nodes)


def test_parent_section_id_copied_from_sectioned() -> None:
  document = EntityDocument(
    metadata=DocumentMetadata(
      document_id="DOC_x",
      filename="policy.txt",
      format=DocumentFormat.TXT,
      title="Acme Policy",
    ),
    entity_clauses=[
      _entity_clause(_clause("S001_C001", "S001", "Rights", "You may access data.")),
      _entity_clause(_clause("S002_C001", "S002", "Delete", "You may delete data.")),
    ],
  )
  sectioned = SectionedDocument(
    metadata=document.metadata,
    full_text="Rights\nYou may access data.\nDelete\nYou may delete data.",
    sections=[
      Section(
        section_id="S001",
        title="Rights",
        text="You may access data.",
        span=Span(start=0, end=20),
        level=1,
        parent_section_id=None,
      ),
      Section(
        section_id="S002",
        title="Delete",
        text="You may delete data.",
        span=Span(start=21, end=40),
        level=2,
        parent_section_id="S001",
      ),
    ],
  )
  graph = policy_view_graph(document, sectioned)
  child = next(node for node in graph.nodes if node.extra.get("section_id") == "S002")
  assert child.extra["parent_section_id"] == "S001"
