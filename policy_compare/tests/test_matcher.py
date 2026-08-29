from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole

from policy_compare.law_loader import load_law_chunks
from policy_compare.matcher import match_graphs
from policy_compare.policy_view import policy_view_graph
from policy_compare.projection import project_ideal_graph

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_law.json"


def _clause(text: str, *, section_id: str = "S002", title: str = "Consent") -> Clause:
  return Clause(
    clause_id=f"{section_id}_C001",
    section_id=section_id,
    section_title=title,
    document_id="DOC_x",
    document_type=DocumentFormat.TXT,
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )


def _document(*clauses: Clause) -> EntityDocument:
  entity_clauses = []
  for clause in clauses:
    classified = ClassifiedClause(
      clause=clause,
      role=StructuralRole.STATEMENT,
      confidence=1.0,
      classification_reason=[],
    )
    entity_clauses.append(
      EntityClause(
        contextual_clause=ContextualClause(classified_clause=classified),
        entities=[],
      )
    )
  return EntityDocument(
    metadata=DocumentMetadata(
      document_id="DOC_x",
      filename="policy.txt",
      format=DocumentFormat.TXT,
    ),
    entity_clauses=entity_clauses,
  )


def test_consent_section_covers_consent_topic() -> None:
  chunks = load_law_chunks([FIXTURE])
  policy = policy_view_graph(
    _document(_clause("We obtain consent before we process personal data. You may withdraw consent.")),
  )
  result = match_graphs(policy, project_ideal_graph(chunks), chunks)
  consent = next(node for node in result.ideal.nodes if node.kind == "topic")
  assert consent.id.startswith("TOPIC_CONSENT@")
  assert consent.status in {"covered", "weak"}
  assert result.links
  assert any(link.topic_id.startswith("TOPIC_CONSENT@") for link in result.links)


def test_unrelated_section_is_extra() -> None:
  chunks = load_law_chunks([FIXTURE])
  policy = policy_view_graph(
    _document(_clause("We host a blog about hiking trails.", section_id="S009", title="Blog")),
  )
  result = match_graphs(policy, project_ideal_graph(chunks), chunks)
  section = next(node for node in result.policy.nodes if node.kind == "section")
  assert section.status == "extra"
  consent = next(node for node in result.ideal.nodes if node.kind == "topic")
  assert consent.status == "missing"


def test_security_section_covers_cyber_security_topic() -> None:
  from policy_compare.models import LawChunk, ViewGraph, ViewNode

  chunks = [
    LawChunk(
      doc_id="IT_CYBER",
      title="Reasonable security practices",
      summary="Body corporates must use reasonable security practices.",
      topic_ids=["TOPIC_CYBER_SECURITY"],
      chunk_type="obligation",
    )
  ]
  policy = ViewGraph(
    nodes=[
      ViewNode(id="doc:1", kind="document", title="Policy"),
      ViewNode(
        id="sec:s15",
        kind="section",
        title="Security",
        summary="We encrypt personal data and take safeguards.",
      ),
    ],
    edges=[],
  )
  ideal = ViewGraph(
    nodes=[ViewNode(id="TOPIC_CYBER_SECURITY@IT", kind="topic", title="Cyber Security")],
    edges=[],
  )
  result = match_graphs(policy, ideal, chunks)
  topic = next(node for node in result.ideal.nodes if node.kind == "topic")
  assert topic.status == "covered"
