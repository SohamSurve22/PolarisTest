"""Neo4j loader using the official Python driver."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neo4j import Driver, GraphDatabase, Session

from graph_builder.cypher_generator import CypherStatement
from graph_builder.exceptions import Neo4jLoaderError


@dataclass(frozen=True)
class Neo4jConfig:
  """Connection settings for Neo4j — no hardcoded credentials."""

  uri: str
  username: str
  password: str
  database: str | None = None


class Neo4jLoader:
  """Executes parameterized Cypher against a Neo4j instance."""

  def __init__(self, config: Neo4jConfig) -> None:
    """Initialize the loader with connection settings.

    Args:
      config: Neo4j URI and authentication credentials.
    """
    self._config = config
    self._driver: Driver | None = None

  def connect(self) -> None:
    """Open a Neo4j driver connection.

    Raises:
      Neo4jLoaderError: If the connection cannot be established.
    """
    if self._driver is not None:
      return

    try:
      self._driver = GraphDatabase.driver(
        self._config.uri,
        auth=(self._config.username, self._config.password),
      )
      self._driver.verify_connectivity()
    except Exception as exc:
      raise Neo4jLoaderError(f"Failed to connect to Neo4j at '{self._config.uri}': {exc}") from exc

  def execute(self, statements: list[CypherStatement]) -> dict[str, int]:
    """Run EXPLAIN on each statement, then execute within a transaction.

    Rolls back the transaction if any statement fails.

    Args:
      statements: Parameterized Cypher statements to execute.

    Returns:
      Dictionary with ``nodes_created`` and ``relationships_created`` counts.

    Raises:
      Neo4jLoaderError: If not connected or execution fails.
    """
    driver = self._require_driver()

    nodes_created = 0
    relationships_created = 0

    try:
      with driver.session(database=self._config.database) as session:
        for statement in statements:
          self._explain(session, statement)

        def _run_transaction(tx: Any) -> tuple[int, int]:
          node_count = 0
          rel_count = 0
          for statement in statements:
            summary = tx.run(statement.query, statement.parameters).consume()
            counters = summary.counters
            node_count += counters.nodes_created
            rel_count += counters.relationships_created
          return node_count, rel_count

        nodes_created, relationships_created = session.execute_write(_run_transaction)
    except Neo4jLoaderError:
      raise
    except Exception as exc:
      raise Neo4jLoaderError(f"Neo4j execution failed: {exc}") from exc

    return {
      "nodes_created": nodes_created,
      "relationships_created": relationships_created,
    }

  def close(self) -> None:
    """Close the Neo4j driver connection."""
    if self._driver is not None:
      self._driver.close()
      self._driver = None

  def _require_driver(self) -> Driver:
    if self._driver is None:
      raise Neo4jLoaderError("Not connected. Call connect() before execute().")
    return self._driver

  def _explain(self, session: Session, statement: CypherStatement) -> None:
    explain_query = f"EXPLAIN {statement.query}"
    try:
      session.run(explain_query, statement.parameters).consume()
    except Exception as exc:
      raise Neo4jLoaderError(
        f"EXPLAIN failed for query '{statement.query}': {exc}",
      ) from exc
