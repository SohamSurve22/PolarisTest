"""Tests for GraphIR models."""

import json

import pytest

from graph_builder.exceptions import LLMGraphBuilderError
from graph_builder.graph_ir import GraphIR, GraphNode
from tests.conftest import sample_graph_ir


class TestGraphNode:
  def test_create_node_with_properties(self) -> None:
    node = GraphNode(
      id="node_1",
      label="Section",
      properties={"number": "43A"},
      source_clause="S001_C001",
    )
    assert node.id == "node_1"
    assert node.label == "Section"
    assert node.properties["number"] == "43A"
    assert node.source_clause == "S001_C001"


class TestGraphIR:
  def test_to_dict_round_trip(self) -> None:
    original = sample_graph_ir()
    restored = GraphIR.from_dict(original.to_dict())

    assert len(restored.nodes) == len(original.nodes)
    assert len(restored.relationships) == len(original.relationships)
    assert restored.nodes[0].id == "law_it_act"
    assert restored.relationships[0].type == "HAS_SECTION"

  def test_from_json_parses_valid_payload(self) -> None:
    payload = json.dumps(sample_graph_ir().to_dict())
    graph_ir = GraphIR.from_json(payload)
    assert len(graph_ir.nodes) == 3
    assert len(graph_ir.relationships) == 2

  def test_from_json_rejects_invalid_json(self) -> None:
    with pytest.raises(LLMGraphBuilderError, match="Invalid JSON"):
      GraphIR.from_json("{not valid json")

  def test_from_dict_rejects_missing_nodes(self) -> None:
    with pytest.raises(LLMGraphBuilderError, match="'nodes'"):
      GraphIR.from_dict({"relationships": []})

  def test_from_dict_rejects_empty_node_id(self) -> None:
    with pytest.raises(LLMGraphBuilderError, match="invalid 'id'"):
      GraphIR.from_dict(
        {
          "nodes": [{"id": "", "label": "Section", "properties": {"a": 1}}],
          "relationships": [],
        },
      )

  def test_from_dict_rejects_invalid_properties(self) -> None:
    with pytest.raises(LLMGraphBuilderError, match="invalid 'properties'"):
      GraphIR.from_dict(
        {
          "nodes": [{"id": "n1", "label": "Section", "properties": "bad"}],
          "relationships": [],
        },
      )

  def test_empty_graph_ir(self) -> None:
    graph_ir = GraphIR()
    assert graph_ir.nodes == []
    assert graph_ir.relationships == []
