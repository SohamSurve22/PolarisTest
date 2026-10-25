"""Load the catalog GraphIR from Neo4j for an explicit analyze-time mode."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship


@dataclass(frozen=True)
class Neo4jScopeConfig:
  uri: str
  username: str
  password: str
  database: str | None = None

  @classmethod
  def from_environment(cls) -> Neo4jScopeConfig:
    return cls(
      uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
      username=os.environ.get("NEO4J_USER", "neo4j"),
      password=os.environ.get("NEO4J_PASSWORD", ""),
      database=os.environ.get("NEO4J_DATABASE") or None,
    )


class Neo4jScopeError(RuntimeError):
  """Raised when Neo4j cannot provide a usable catalog graph."""


_LABEL_TO_GRAPH: dict[str, str] = {
  "Document": "LawVersion",
  "Act": "Act",
  "Chapter": "Chapter",
  "Part": "Part",
  "Section": "Section",
  "Clause": "Clause",
  "Entity": "Entity",
  "Obligation": "Obligation",
  "Penalty": "Penalty",
  "UnresolvedReference": "UnresolvedReference",
}


def graph_ir_from_neo4j(
  config: Neo4jScopeConfig | None = None,
  *,
  driver_factory: Callable[..., Any] | None = None,
) -> GraphIR:
  """Read exported nodes and relationships through parameterized Cypher."""
  settings = config or Neo4jScopeConfig.from_environment()
  if driver_factory is None:
    try:
      from neo4j import GraphDatabase
    except ImportError as exc:
      raise Neo4jScopeError("The neo4j Python driver is not installed") from exc
    driver_factory = GraphDatabase.driver

  driver = None
  try:
    driver = driver_factory(settings.uri, auth=(settings.username, settings.password))
    verify = getattr(driver, "verify_connectivity", None)
    if callable(verify):
      verify()
    with driver.session(database=settings.database) as session:
      node_rows = list(session.run(
        "MATCH (n) WHERE n.id IS NOT NULL "
        "RETURN n.id AS id, labels(n) AS labels, properties(n) AS properties",
      ))
      relationship_rows = list(session.run(
        "MATCH (source)-[r]->(target) "
        "WHERE source.id IS NOT NULL AND target.id IS NOT NULL "
        "RETURN source.id AS source, target.id AS target, type(r) AS type, "
        "properties(r) AS properties",
      ))
  except Neo4jScopeError:
    raise
  except Exception as exc:
    raise Neo4jScopeError(f"Failed to load catalog GraphIR from Neo4j: {exc}") from exc
  finally:
    if driver is not None:
      close = getattr(driver, "close", None)
      if callable(close):
        close()

  nodes = [_node_from_row(row) for row in node_rows]
  relationships = [_relationship_from_row(row) for row in relationship_rows]
  if not nodes:
    raise Neo4jScopeError("Neo4j returned no catalog nodes")
  return GraphIR(nodes=nodes, relationships=relationships)


def _node_from_row(row: Any) -> GraphNode:
  raw_labels = row.get("labels", []) if hasattr(row, "get") else []
  labels = [str(item) for item in raw_labels]
  label = next((_LABEL_TO_GRAPH[item] for item in labels if item in _LABEL_TO_GRAPH), labels[0] if labels else "Node")
  properties = row.get("properties", {}) if hasattr(row, "get") else {}
  return GraphNode(
    id=str(row.get("id", "")),
    label=label,
    properties=dict(properties or {}),
    source_clause=(properties or {}).get("source_clause"),
  )


def _relationship_from_row(row: Any) -> GraphRelationship:
  return GraphRelationship(
    source=str(row.get("source", "")),
    target=str(row.get("target", "")),
    type=str(row.get("type", "")),
    properties=dict(row.get("properties", {}) or {}),
  )
