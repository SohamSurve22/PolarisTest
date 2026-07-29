"""Validation rules for graph intermediate representation."""

from __future__ import annotations

from graph_builder.exceptions import GraphValidationError
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship
from graph_builder.graph_models import ALLOWED_NODE_LABELS, ALLOWED_RELATIONSHIP_TYPES


class GraphValidator:
  """Validates graph IR before Cypher generation or Neo4j loading."""

  def validate(self, graph_ir: GraphIR) -> list[str]:
    """Validate a graph IR instance.

    Args:
      graph_ir: Graph intermediate representation to validate.

    Returns:
      Non-fatal validation warnings (currently unused, reserved for soft checks).

    Raises:
      GraphValidationError: If any hard validation rule is violated.
    """
    warnings: list[str] = []

    if not graph_ir.nodes:
      raise GraphValidationError("Graph is empty: at least one node is required.")

    self._validate_nodes(graph_ir.nodes)
    node_ids = {node.id for node in graph_ir.nodes}
    self._validate_relationships(graph_ir.relationships, node_ids)

    return warnings

  def _validate_nodes(self, nodes: list[GraphNode]) -> None:
    seen_ids: set[str] = set()

    for node in nodes:
      if node.label not in ALLOWED_NODE_LABELS:
        raise GraphValidationError(
          f"Unknown node label '{node.label}' on node '{node.id}'. "
          f"Allowed labels: {sorted(ALLOWED_NODE_LABELS)}",
        )

      if not node.properties:
        raise GraphValidationError(f"Node '{node.id}' has empty properties.")

      if node.id in seen_ids:
        raise GraphValidationError(f"Duplicate node ID '{node.id}'.")
      seen_ids.add(node.id)

  def _validate_relationships(
    self,
    relationships: list[GraphRelationship],
    node_ids: set[str],
  ) -> None:
    for rel in relationships:
      if rel.type not in ALLOWED_RELATIONSHIP_TYPES:
        raise GraphValidationError(
          f"Unknown relationship type '{rel.type}' "
          f"from '{rel.source}' to '{rel.target}'. "
          f"Allowed types: {sorted(ALLOWED_RELATIONSHIP_TYPES)}",
        )

      if rel.source not in node_ids:
        raise GraphValidationError(
          f"Relationship source '{rel.source}' does not match any node ID.",
        )

      if rel.target not in node_ids:
        raise GraphValidationError(
          f"Relationship target '{rel.target}' does not match any node ID.",
        )

      if rel.source == rel.target:
        raise GraphValidationError(
          f"Self-referencing relationship detected on node '{rel.source}' "
          f"with type '{rel.type}'.",
        )
