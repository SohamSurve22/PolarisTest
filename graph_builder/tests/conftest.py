"""Shared test fixtures for graph builder tests."""

from __future__ import annotations

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship


def sample_graph_ir() -> GraphIR:
  """Return a minimal valid graph IR for testing."""
  return GraphIR(
    nodes=[
      GraphNode(
        id="law_it_act",
        label="LawVersion",
        properties={"name": "Information Technology Act, 2000"},
        source_clause=None,
      ),
      GraphNode(
        id="section_43a",
        label="Section",
        properties={"number": "43A", "title": "Compensation for failure to protect data"},
        source_clause="S001_C001",
      ),
      GraphNode(
        id="obligation_protect",
        label="Obligation",
        properties={"text": "Body corporate shall implement reasonable security practices"},
        source_clause="S001_C001",
      ),
    ],
    relationships=[
      GraphRelationship(
        source="law_it_act",
        target="section_43a",
        type="HAS_SECTION",
        properties={},
      ),
      GraphRelationship(
        source="section_43a",
        target="obligation_protect",
        type="IMPOSES",
        properties={},
      ),
    ],
  )


def sample_graph_json() -> str:
  """Return sample GraphIR as a JSON string."""
  import json

  return json.dumps(sample_graph_ir().to_dict())
