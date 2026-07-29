"""Graph Intermediate Representation models.

The LLM produces ``GraphIR`` JSON — never Cypher.  Downstream stages
convert validated IR into deterministic MERGE statements.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from graph_builder.exceptions import LLMGraphBuilderError


@dataclass
class GraphNode:
  """A node in the knowledge graph intermediate representation."""

  id: str
  label: str
  properties: dict[str, Any] = field(default_factory=dict)
  source_clause: str | None = None


@dataclass
class GraphRelationship:
  """A directed relationship between two graph nodes."""

  source: str
  target: str
  type: str
  properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphIR:
  """Complete graph intermediate representation produced by the LLM."""

  nodes: list[GraphNode] = field(default_factory=list)
  relationships: list[GraphRelationship] = field(default_factory=list)

  def to_dict(self) -> dict[str, Any]:
    """Serialize the graph IR to a JSON-compatible dictionary.

    Returns:
      Dictionary with ``nodes`` and ``relationships`` keys.
    """
    return {
      "nodes": [
        {
          "id": node.id,
          "label": node.label,
          "properties": node.properties,
          "source_clause": node.source_clause,
        }
        for node in self.nodes
      ],
      "relationships": [
        {
          "source": rel.source,
          "target": rel.target,
          "type": rel.type,
          "properties": rel.properties,
        }
        for rel in self.relationships
      ],
    }

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> GraphIR:
    """Construct a ``GraphIR`` from a parsed JSON dictionary.

    Args:
      data: Parsed JSON object with ``nodes`` and ``relationships``.

    Returns:
      Populated ``GraphIR`` instance.

    Raises:
      LLMGraphBuilderError: If required fields are missing or malformed.
    """
    if not isinstance(data, dict):
      raise LLMGraphBuilderError("Graph IR payload must be a JSON object.")

    raw_nodes = data.get("nodes")
    raw_relationships = data.get("relationships")

    if not isinstance(raw_nodes, list):
      raise LLMGraphBuilderError("'nodes' must be a JSON array.")
    if not isinstance(raw_relationships, list):
      raise LLMGraphBuilderError("'relationships' must be a JSON array.")

    nodes: list[GraphNode] = []
    for index, raw_node in enumerate(raw_nodes):
      if not isinstance(raw_node, dict):
        raise LLMGraphBuilderError(f"Node at index {index} must be a JSON object.")

      node_id = raw_node.get("id")
      label = raw_node.get("label")
      if not isinstance(node_id, str) or not node_id.strip():
        raise LLMGraphBuilderError(f"Node at index {index} has an invalid 'id'.")
      if not isinstance(label, str) or not label.strip():
        raise LLMGraphBuilderError(f"Node at index {index} has an invalid 'label'.")

      properties = raw_node.get("properties", {})
      if not isinstance(properties, dict):
        raise LLMGraphBuilderError(f"Node '{node_id}' has invalid 'properties'.")

      source_clause = raw_node.get("source_clause")
      if source_clause is not None and not isinstance(source_clause, str):
        raise LLMGraphBuilderError(f"Node '{node_id}' has invalid 'source_clause'.")

      nodes.append(
        GraphNode(
          id=node_id.strip(),
          label=label.strip(),
          properties=properties,
          source_clause=source_clause,
        ),
      )

    relationships: list[GraphRelationship] = []
    for index, raw_rel in enumerate(raw_relationships):
      if not isinstance(raw_rel, dict):
        raise LLMGraphBuilderError(f"Relationship at index {index} must be a JSON object.")

      source = raw_rel.get("source")
      target = raw_rel.get("target")
      rel_type = raw_rel.get("type")
      if not isinstance(source, str) or not source.strip():
        raise LLMGraphBuilderError(f"Relationship at index {index} has invalid 'source'.")
      if not isinstance(target, str) or not target.strip():
        raise LLMGraphBuilderError(f"Relationship at index {index} has invalid 'target'.")
      if not isinstance(rel_type, str) or not rel_type.strip():
        raise LLMGraphBuilderError(f"Relationship at index {index} has invalid 'type'.")

      properties = raw_rel.get("properties", {})
      if not isinstance(properties, dict):
        raise LLMGraphBuilderError(
          f"Relationship '{source}' -> '{target}' has invalid 'properties'.",
        )

      relationships.append(
        GraphRelationship(
          source=source.strip(),
          target=target.strip(),
          type=rel_type.strip(),
          properties=properties,
        ),
      )

    return cls(nodes=nodes, relationships=relationships)

  @classmethod
  def from_json(cls, payload: str) -> GraphIR:
    """Parse a JSON string into a ``GraphIR``.

    Args:
      payload: Raw JSON string from the LLM.

    Returns:
      Parsed ``GraphIR`` instance.

    Raises:
      LLMGraphBuilderError: If JSON is invalid or structure is wrong.
    """
    try:
      data = json.loads(payload)
    except json.JSONDecodeError as exc:
      raise LLMGraphBuilderError(f"Invalid JSON from LLM: {exc}") from exc
    return cls.from_dict(data)
