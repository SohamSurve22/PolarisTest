"""Deterministic Cypher generation from validated graph IR."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from graph_builder.exceptions import CypherGenerationError
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

_VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class CypherStatement:
  """A parameterized Cypher statement ready for Neo4j execution."""

  query: str
  parameters: dict[str, Any] = field(default_factory=dict)


class CypherGenerator:
  """Converts validated ``GraphIR`` into MERGE-based Cypher statements."""

  def generate(self, graph_ir: GraphIR) -> list[CypherStatement]:
    """Generate Cypher MERGE statements for all nodes and relationships.

    Nodes are emitted first, then relationships.  All statements use MERGE —
    never CREATE.

    Args:
      graph_ir: Validated graph intermediate representation.

    Returns:
      Ordered list of parameterized Cypher statements.

    Raises:
      CypherGenerationError: If labels or relationship types are invalid identifiers.
    """
    statements: list[CypherStatement] = []

    for index, node in enumerate(graph_ir.nodes):
      statements.append(self._merge_node(node, index))

    for index, relationship in enumerate(graph_ir.relationships):
      statements.append(self._merge_relationship(relationship, index))

    return statements

  def _merge_node(self, node: GraphNode, index: int) -> CypherStatement:
    label = self._sanitize_identifier(node.label, "node label")
    param_prefix = f"n{index}"

    properties = dict(node.properties)
    properties["id"] = node.id
    if node.source_clause is not None:
      properties["source_clause"] = node.source_clause

    query = (
      f"MERGE (n:{label} {{id: ${param_prefix}_id}}) "
      f"SET n += ${param_prefix}_props"
    )
    return CypherStatement(
      query=query,
      parameters={
        f"{param_prefix}_id": node.id,
        f"{param_prefix}_props": properties,
      },
    )

  def _merge_relationship(
    self,
    relationship: GraphRelationship,
    index: int,
  ) -> CypherStatement:
    rel_type = self._sanitize_identifier(relationship.type, "relationship type")
    param_prefix = f"r{index}"

    query = (
      "MATCH (source {id: $source_id}) "
      "MATCH (target {id: $target_id}) "
      f"MERGE (source)-[r:{rel_type}]->(target) "
      f"SET r += ${param_prefix}_props"
    )
    return CypherStatement(
      query=query,
      parameters={
        "source_id": relationship.source,
        "target_id": relationship.target,
        f"{param_prefix}_props": dict(relationship.properties),
      },
    )

  def _sanitize_identifier(self, value: str, kind: str) -> str:
    if not _VALID_IDENTIFIER.match(value):
      raise CypherGenerationError(
        f"Invalid {kind} '{value}': must match {_VALID_IDENTIFIER.pattern}.",
      )
    return value
