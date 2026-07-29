"""Tests for Neo4j loader with mocked driver."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from graph_builder.cypher_generator import CypherStatement
from graph_builder.exceptions import Neo4jLoaderError
from graph_builder.neo4j_loader import Neo4jConfig, Neo4jLoader


def _make_summary(nodes: int = 1, rels: int = 1) -> MagicMock:
  summary = MagicMock()
  summary.counters.nodes_created = nodes
  summary.counters.relationships_created = rels
  return summary


class TestNeo4jLoader:
  def setup_method(self) -> None:
    self.config = Neo4jConfig(
      uri="bolt://localhost:7687",
      username="neo4j",
      password="test-password",
    )
    self.loader = Neo4jLoader(self.config)

  def test_execute_without_connect_raises(self) -> None:
    with pytest.raises(Neo4jLoaderError, match="Not connected"):
      self.loader.execute([])

  @patch("graph_builder.neo4j_loader.GraphDatabase")
  def test_connect_and_execute(self, mock_graph_db: MagicMock) -> None:
    mock_driver = MagicMock()
    mock_graph_db.driver.return_value = mock_driver

    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    explain_result = MagicMock()
    explain_result.consume.return_value = _make_summary(0, 0)

    tx_result = MagicMock()
    tx_result.consume.return_value = _make_summary(1, 1)

    def run_side_effect(query: str, parameters: dict[str, Any]) -> MagicMock:
      if query.startswith("EXPLAIN"):
        return explain_result
      return tx_result

    mock_session.run.side_effect = run_side_effect
    mock_session.execute_write.side_effect = lambda fn: fn(MagicMock(run=run_side_effect))

    self.loader.connect()
    statements = [
      CypherStatement(
        query="MERGE (n:Section {id: $n0_id}) SET n += $n0_props",
        parameters={"n0_id": "s1", "n0_props": {"name": "43A"}},
      ),
    ]
    stats = self.loader.execute(statements)

    assert stats["nodes_created"] == 1
    assert stats["relationships_created"] == 1
    mock_driver.verify_connectivity.assert_called_once()

  @patch("graph_builder.neo4j_loader.GraphDatabase")
  def test_connect_failure_raises(self, mock_graph_db: MagicMock) -> None:
    mock_graph_db.driver.side_effect = RuntimeError("connection refused")

    with pytest.raises(Neo4jLoaderError, match="Failed to connect"):
      self.loader.connect()

  @patch("graph_builder.neo4j_loader.GraphDatabase")
  def test_explain_failure_raises(self, mock_graph_db: MagicMock) -> None:
    mock_driver = MagicMock()
    mock_graph_db.driver.return_value = mock_driver

    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.side_effect = RuntimeError("invalid cypher")

    self.loader.connect()
    statements = [CypherStatement(query="MERGE (n:Bad {id: $id})", parameters={"id": "x"})]

    with pytest.raises(Neo4jLoaderError, match="EXPLAIN failed"):
      self.loader.execute(statements)

  @patch("graph_builder.neo4j_loader.GraphDatabase")
  def test_close_closes_driver(self, mock_graph_db: MagicMock) -> None:
    mock_driver = MagicMock()
    mock_graph_db.driver.return_value = mock_driver

    self.loader.connect()
    self.loader.close()

    mock_driver.close.assert_called_once()
