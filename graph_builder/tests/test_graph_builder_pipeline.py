"""Tests for graph builder pipeline orchestration."""

from unittest.mock import MagicMock, patch

from graph_builder.graph_builder_pipeline import GraphBuilderPipeline
from graph_builder.graph_validator import GraphValidator
from graph_builder.llm_graph_builder import LLMGraphBuilder
from graph_builder.neo4j_loader import Neo4jConfig, Neo4jLoader
from tests.conftest import sample_graph_ir, sample_graph_json


class FakeLLMClient:
  def __init__(self, response: str) -> None:
    self.response = response

  def generate(self, system_prompt: str, user_prompt: str) -> str:
    return self.response


class TestGraphBuilderPipeline:
  def _entity_document(self) -> object:
    from document_pipeline.models.entity import EntityDocument
    from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata

    return EntityDocument(
      metadata=DocumentMetadata(
        document_id="DOC_pipeline",
        filename="act.txt",
        format=DocumentFormat.TXT,
      ),
    )

  def test_build_without_neo4j_loader(self) -> None:
    llm_builder = LLMGraphBuilder(FakeLLMClient(sample_graph_json()))
    pipeline = GraphBuilderPipeline(llm_builder=llm_builder)

    stats = pipeline.build(self._entity_document())  # type: ignore[arg-type]

    assert stats.nodes_in_ir == 3
    assert stats.relationships_in_ir == 2
    assert stats.nodes_created == 0
    assert stats.relationships_created == 0
    assert stats.execution_time_ms >= 0

  def test_build_from_ir_skips_llm(self) -> None:
    llm_builder = LLMGraphBuilder(FakeLLMClient(""))
    pipeline = GraphBuilderPipeline(llm_builder=llm_builder)

    stats = pipeline.build_from_ir(sample_graph_ir())

    assert stats.nodes_in_ir == 3
    assert stats.relationships_in_ir == 2

  def test_generate_cypher_validates_and_returns_statements(self) -> None:
    llm_builder = LLMGraphBuilder(FakeLLMClient(""))
    pipeline = GraphBuilderPipeline(llm_builder=llm_builder)

    statements = pipeline.generate_cypher(sample_graph_ir())

    assert len(statements) == 5
    assert all("MERGE" in s.query for s in statements)

  @patch("graph_builder.neo4j_loader.GraphDatabase")
  def test_build_with_neo4j_loader(self, mock_graph_db: MagicMock) -> None:
    mock_driver = MagicMock()
    mock_graph_db.driver.return_value = mock_driver

    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    explain_result = MagicMock()
    explain_result.consume.return_value = MagicMock(
      counters=MagicMock(nodes_created=0, relationships_created=0),
    )

    node_summary = MagicMock()
    node_summary.counters.nodes_created = 1
    node_summary.counters.relationships_created = 0
    node_result = MagicMock()
    node_result.consume.return_value = node_summary

    rel_summary = MagicMock()
    rel_summary.counters.nodes_created = 0
    rel_summary.counters.relationships_created = 1
    rel_result = MagicMock()
    rel_result.consume.return_value = rel_summary

    call_count: list[int] = [0]

    def run_side_effect(query: str, parameters: dict[str, object]) -> MagicMock:
      if query.startswith("EXPLAIN"):
        return explain_result
      idx = call_count[0]
      call_count[0] += 1
      return node_result if idx < 3 else rel_result

    mock_session.run.side_effect = run_side_effect
    mock_session.execute_write.side_effect = lambda fn: fn(MagicMock(run=run_side_effect))

    config = Neo4jConfig(uri="bolt://localhost:7687", username="neo4j", password="pw")
    loader = Neo4jLoader(config)
    llm_builder = LLMGraphBuilder(FakeLLMClient(sample_graph_json()))
    pipeline = GraphBuilderPipeline(llm_builder=llm_builder, neo4j_loader=loader)

    stats = pipeline.build(self._entity_document())  # type: ignore[arg-type]

    assert stats.nodes_created == 3
    assert stats.relationships_created == 2

  def test_dependency_injection(self) -> None:
    custom_validator = GraphValidator()
    llm_builder = LLMGraphBuilder(FakeLLMClient(sample_graph_json()))
    pipeline = GraphBuilderPipeline(
      llm_builder=llm_builder,
      validator=custom_validator,
    )

    stats = pipeline.build_from_ir(sample_graph_ir())
    assert stats.nodes_in_ir == 3
