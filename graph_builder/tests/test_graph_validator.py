"""Tests for graph IR validation."""

import pytest

from graph_builder.exceptions import GraphValidationError
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship
from graph_builder.graph_validator import GraphValidator
from tests.conftest import sample_graph_ir


class TestGraphValidator:
  def setup_method(self) -> None:
    self.validator = GraphValidator()

  def test_valid_graph_passes(self) -> None:
    warnings = self.validator.validate(sample_graph_ir())
    assert warnings == []

  def test_rejects_empty_graph(self) -> None:
    with pytest.raises(GraphValidationError, match="empty"):
      self.validator.validate(GraphIR())

  def test_rejects_unknown_node_label(self) -> None:
    graph = GraphIR(
      nodes=[GraphNode(id="n1", label="UnknownLabel", properties={"name": "x"})],
    )
    with pytest.raises(GraphValidationError, match="Unknown node label"):
      self.validator.validate(graph)

  def test_rejects_unknown_relationship_type(self) -> None:
    graph = GraphIR(
      nodes=[
        GraphNode(id="a", label="Section", properties={"name": "A"}),
        GraphNode(id="b", label="Section", properties={"name": "B"}),
      ],
      relationships=[
        GraphRelationship(source="a", target="b", type="UNKNOWN_REL"),
      ],
    )
    with pytest.raises(GraphValidationError, match="Unknown relationship type"):
      self.validator.validate(graph)

  def test_accepts_has_obligation_relationship(self) -> None:
    """HAS_OBLIGATION is emitted by semantic enrichment and must validate."""
    graph = GraphIR(
      nodes=[
        GraphNode(id="c1", label="Clause", properties={"name": "C1"}),
        GraphNode(id="o1", label="Obligation", properties={"subject": "x"}),
      ],
      relationships=[
        GraphRelationship(source="c1", target="o1", type="HAS_OBLIGATION"),
      ],
    )
    assert self.validator.validate(graph) == []

  def test_rejects_duplicate_node_ids(self) -> None:
    graph = GraphIR(
      nodes=[
        GraphNode(id="dup", label="Section", properties={"name": "A"}),
        GraphNode(id="dup", label="Rule", properties={"name": "B"}),
      ],
    )
    with pytest.raises(GraphValidationError, match="Duplicate node ID"):
      self.validator.validate(graph)

  def test_rejects_missing_relationship_source(self) -> None:
    graph = GraphIR(
      nodes=[GraphNode(id="a", label="Section", properties={"name": "A"})],
      relationships=[
        GraphRelationship(source="missing", target="a", type="REFERENCES"),
      ],
    )
    with pytest.raises(GraphValidationError, match="source"):
      self.validator.validate(graph)

  def test_rejects_missing_relationship_target(self) -> None:
    graph = GraphIR(
      nodes=[GraphNode(id="a", label="Section", properties={"name": "A"})],
      relationships=[
        GraphRelationship(source="a", target="missing", type="REFERENCES"),
      ],
    )
    with pytest.raises(GraphValidationError, match="target"):
      self.validator.validate(graph)

  def test_rejects_empty_node_properties(self) -> None:
    graph = GraphIR(
      nodes=[GraphNode(id="n1", label="Section", properties={})],
    )
    with pytest.raises(GraphValidationError, match="empty properties"):
      self.validator.validate(graph)

  def test_rejects_self_referencing_relationship(self) -> None:
    graph = GraphIR(
      nodes=[GraphNode(id="a", label="Section", properties={"name": "A"})],
      relationships=[
        GraphRelationship(source="a", target="a", type="REFERENCES"),
      ],
    )
    with pytest.raises(GraphValidationError, match="Self-referencing"):
      self.validator.validate(graph)

  def test_rejects_invalid_triple(self) -> None:
    graph = GraphIR(
      nodes=[
        GraphNode(id="a", label="Actor", properties={"name": "we"}),
        GraphNode(id="b", label="PersonalData", properties={"name": "email"}),
      ],
      relationships=[
        GraphRelationship(source="a", target="b", type="PENALIZES"),
      ],
    )
    with pytest.raises(GraphValidationError, match="Invalid triple"):
      self.validator.validate(graph)

  def test_validate_policy_allows_empty(self) -> None:
    warnings = self.validator.validate_policy(GraphIR())
    assert warnings
