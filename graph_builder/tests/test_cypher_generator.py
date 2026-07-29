"""Tests for deterministic Cypher generation."""

from graph_builder.cypher_generator import CypherGenerator
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship
from tests.conftest import sample_graph_ir


class TestCypherGenerator:
  def setup_method(self) -> None:
    self.generator = CypherGenerator()

  def test_generates_merge_statements(self) -> None:
    statements = self.generator.generate(sample_graph_ir())

    assert len(statements) == 5  # 3 nodes + 2 relationships
    for statement in statements:
      assert "MERGE" in statement.query
      assert "CREATE" not in statement.query

  def test_nodes_generated_before_relationships(self) -> None:
    statements = self.generator.generate(sample_graph_ir())

    node_statements = [s for s in statements if "(n:" in s.query]
    rel_statements = [s for s in statements if "-[r:" in s.query]

    assert len(node_statements) == 3
    assert len(rel_statements) == 2
    assert statements.index(node_statements[-1]) < statements.index(rel_statements[0])

  def test_node_merge_uses_parameterized_id_and_props(self) -> None:
    statements = self.generator.generate(sample_graph_ir())
    node_stmt = statements[0]

    assert "MERGE (n:LawVersion {id: $n0_id})" in node_stmt.query
    assert "SET n += $n0_props" in node_stmt.query
    assert node_stmt.parameters["n0_id"] == "law_it_act"
    assert node_stmt.parameters["n0_props"]["name"] == "Information Technology Act, 2000"

  def test_relationship_merge_uses_match_and_merge(self) -> None:
    statements = self.generator.generate(sample_graph_ir())
    rel_stmt = next(s for s in statements if "-[r:" in s.query)

    assert "MATCH (source {id: $source_id})" in rel_stmt.query
    assert "MATCH (target {id: $target_id})" in rel_stmt.query
    assert "MERGE (source)-[r:HAS_SECTION]->(target)" in rel_stmt.query
    assert rel_stmt.parameters["source_id"] == "law_it_act"
    assert rel_stmt.parameters["target_id"] == "section_43a"

  def test_source_clause_included_in_node_properties(self) -> None:
    graph = GraphIR(
      nodes=[
        GraphNode(
          id="c1",
          label="Clause",
          properties={"text": "sample"},
          source_clause="S001_C001",
        ),
      ],
    )
    statements = self.generator.generate(graph)
    assert statements[0].parameters["n0_props"]["source_clause"] == "S001_C001"

  def test_relationship_properties_parameterized(self) -> None:
    graph = GraphIR(
      nodes=[
        GraphNode(id="a", label="Section", properties={"name": "A"}),
        GraphNode(id="b", label="Obligation", properties={"name": "B"}),
      ],
      relationships=[
        GraphRelationship(
          source="a",
          target="b",
          type="IMPOSES",
          properties={"severity": "high"},
        ),
      ],
    )
    statements = self.generator.generate(graph)
    rel_stmt = statements[-1]
    assert rel_stmt.parameters["r0_props"] == {"severity": "high"}
