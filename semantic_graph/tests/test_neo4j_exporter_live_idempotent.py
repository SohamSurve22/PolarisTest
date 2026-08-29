"""Live Neo4j tests: re-exporting the same GraphIR must not duplicate graph."""

from __future__ import annotations

import os
import uuid

import pytest
from neo4j import Driver, GraphDatabase

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from semantic_graph.neo4j_exporter import Neo4jExporter

pytestmark = pytest.mark.neo4j


def _neo4j_auth() -> tuple[str, str, str]:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "polarislex")
    return uri, user, password


@pytest.fixture(scope="module")
def neo4j_driver() -> Driver:
    uri, user, password = _neo4j_auth()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
    except Exception as exc:
        driver.close()
        pytest.skip(f"Neo4j not running at {uri}: {exc}")
    yield driver
    driver.close()


@pytest.fixture
def graph_prefix() -> str:
    return f"sg_it_{uuid.uuid4().hex[:12]}_"


@pytest.fixture
def sample_graph(graph_prefix: str) -> GraphIR:
    doc_id = f"{graph_prefix}doc"
    section_id = f"{graph_prefix}sec"
    clause_id = f"{graph_prefix}clause"
    return GraphIR(
        nodes=[
            GraphNode(
                id=doc_id,
                label="LawVersion",
                properties={"name": "Idempotent live test act"},
            ),
            GraphNode(
                id=section_id,
                label="Section",
                properties={"number": "1", "title": "Scope"},
            ),
            GraphNode(
                id=clause_id,
                label="Clause",
                properties={"text": "This statute applies to personal data."},
                source_clause="S001_C001",
            ),
        ],
        relationships=[
            GraphRelationship(source=doc_id, target=section_id, type="HAS_SECTION"),
            GraphRelationship(source=section_id, target=clause_id, type="HAS_CLAUSE"),
        ],
    )


def _purge(driver: Driver, prefix: str) -> None:
    with driver.session() as session:
        session.run(
            "MATCH (n) WHERE n.id STARTS WITH $prefix DETACH DELETE n",
            prefix=prefix,
        ).consume()


def _counts(driver: Driver, prefix: str) -> tuple[int, int]:
    with driver.session() as session:
        nodes = session.run(
            "MATCH (n) WHERE n.id STARTS WITH $prefix RETURN count(n) AS c",
            prefix=prefix,
        ).single()["c"]
        rels = session.run(
            "MATCH (a)-[r]->(b) "
            "WHERE a.id STARTS WITH $prefix AND b.id STARTS WITH $prefix "
            "RETURN count(r) AS c",
            prefix=prefix,
        ).single()["c"]
    return int(nodes), int(rels)


@pytest.fixture(autouse=True)
def _isolated_subgraph(neo4j_driver: Driver, graph_prefix: str):
    _purge(neo4j_driver, graph_prefix)
    yield
    _purge(neo4j_driver, graph_prefix)


def test_second_export_creates_zero_nodes_and_relationships(
    neo4j_driver: Driver,
    sample_graph: GraphIR,
    graph_prefix: str,
) -> None:
    exporter = Neo4jExporter(driver=neo4j_driver)
    first = exporter.export(sample_graph)
    assert first["nodes_created"] == 3
    assert first["relationships_created"] == 2
    assert _counts(neo4j_driver, graph_prefix) == (3, 2)

    second = exporter.export(sample_graph)
    assert second["nodes_created"] == 0
    assert second["relationships_created"] == 0
    assert _counts(neo4j_driver, graph_prefix) == (3, 2)


def test_reexport_updates_properties_without_duplicating(
    neo4j_driver: Driver,
    sample_graph: GraphIR,
    graph_prefix: str,
) -> None:
    exporter = Neo4jExporter(driver=neo4j_driver)
    exporter.export(sample_graph)

    updated = GraphIR(
        nodes=[
            GraphNode(
                id=node.id,
                label=node.label,
                properties={**node.properties, "title": "Updated scope"}
                if node.label == "Section"
                else dict(node.properties),
                source_clause=node.source_clause,
            )
            for node in sample_graph.nodes
        ],
        relationships=list(sample_graph.relationships),
    )
    stats = exporter.export(updated)
    assert stats["nodes_created"] == 0
    assert stats["relationships_created"] == 0
    assert _counts(neo4j_driver, graph_prefix) == (3, 2)

    section_id = f"{graph_prefix}sec"
    with neo4j_driver.session() as session:
        title = session.run(
            "MATCH (n {id: $id}) RETURN n.title AS title",
            id=section_id,
        ).single()["title"]
    assert title == "Updated scope"
