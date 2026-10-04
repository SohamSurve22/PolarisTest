"""Tests for OpenIE → constrained policy GraphIR."""

from graph_builder.graph_models import ALLOWED_NODE_LABELS, ALLOWED_RELATIONSHIP_TYPES
from graph_builder.graph_validator import GraphValidator
from graph_builder.llm_graph_builder import LLMGraphBuilder
from graph_builder.openie import OpenIEExtractor
from graph_builder.policy_graph_builder import PolicyGraphBuilder, propositions_to_graph_ir
from graph_builder.propositions import RawProposition
from graph_builder.graph_builder_pipeline import GraphBuilderPipeline
from tests.conftest import sample_graph_json


def _prop(
  subject: str,
  predicate: str,
  obj: str,
  *,
  clause_id: str = "S001_C001",
) -> RawProposition:
  return RawProposition(
    subject=subject,
    predicate=predicate,
    object=obj,
    evidence=f"{subject} {predicate} {obj}.",
    source_clause_id=clause_id,
    document_id="DOC_x",
  )


class TestPropositionsToGraphIR:
  def test_collect_email_becomes_canonical_edge(self) -> None:
    graph, failures = propositions_to_graph_ir(
      [_prop("we", "gathers", "email address")],
      document_id="DOC_x",
    )
    assert failures == []
    labels = {node.label for node in graph.nodes}
    assert labels <= ALLOWED_NODE_LABELS
    assert {rel.type for rel in graph.relationships} <= ALLOWED_RELATIONSHIP_TYPES
    assert any(rel.type == "COLLECTS" for rel in graph.relationships)
    assert all(node.source_clause or node.id for node in graph.nodes)
    GraphValidator().validate(graph)

  def test_owns_is_rejected_not_emitted(self) -> None:
    graph, failures = propositions_to_graph_ir(
      [_prop("we", "owns", "email address")],
      document_id="DOC_x",
    )
    assert graph.relationships == []
    assert any(item.status == "UNMAPPED_RELATION" for item in failures)
    assert all("OWNS" not in rel.type for rel in graph.relationships)

  def test_unknown_entity_is_retained_as_failure(self) -> None:
    graph, failures = propositions_to_graph_ir(
      [_prop("we", "collect", "moon rocks")],
      document_id="DOC_x",
    )
    assert graph.relationships == []
    assert any(item.status == "UNMAPPED_ENTITY" for item in failures)

  def test_duplicate_nodes_are_merged(self) -> None:
    graph, failures = propositions_to_graph_ir(
      [
        _prop("we", "collect", "email"),
        _prop("we", "collect", "email address"),
      ],
      document_id="DOC_x",
    )
    assert failures == []
    assert len(graph.nodes) == 2
    assert len(graph.relationships) == 1


class TestPolicyGraphBuilderPipeline:
  def test_policy_builder_path_skips_llm_graphir(self) -> None:
    from document_pipeline.models.entity import EntityDocument
    from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata

    spo = """
    {"propositions": [
      {"subject": "we", "predicate": "collect", "object": "email",
       "evidence": "We collect email.", "clause_id": "S001_C001"}
    ]}
    """
    document = EntityDocument(
      metadata=DocumentMetadata(
        document_id="DOC_x",
        filename="policy.txt",
        format=DocumentFormat.TXT,
      ),
    )
    llm_builder = LLMGraphBuilder(_Fake(sample_graph_json()))
    policy_builder = PolicyGraphBuilder(OpenIEExtractor(_Fake(spo)))
    pipeline = GraphBuilderPipeline(llm_builder=llm_builder, policy_builder=policy_builder)
    stats = pipeline.build(document)
    assert stats.relationships_in_ir == 1
    assert stats.mapping_failures == []
    assert stats.nodes_created == 0


class _Fake:
  def __init__(self, response: str) -> None:
    self.response = response

  def generate(self, system_prompt: str, user_prompt: str) -> str:
    return self.response
