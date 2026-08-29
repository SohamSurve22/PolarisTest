"""Live Neo4j tests: CypherGenerator + Neo4jLoader re-ingest must not duplicate."""

from __future__ import annotations

import os
import uuid

import pytest
from neo4j import Driver, GraphDatabase

from graph_builder.cypher_generator import CypherGenerator
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship
from graph_builder.neo4j_loader import Neo4jConfig, Neo4jLoader

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
    return f"gb_it_{uuid.uuid4().hex[:12]}_"


@pytest.fixture
def sample_graph(graph_prefix: str) -> GraphIR:
    law_id = f"{graph_prefix}law"
    section_id = f"{graph_prefix}sec"
    obligation_id = f"{graph_prefix}obl"
    return GraphIR(
        nodes=[
            GraphNode(
                id=law_id,
                label="LawVersion",
                properties={"name": "IT Act live re-ingest"},
            ),
            GraphNode(
                id=section_id,
                label="Section",
                properties={"number": "43A", "title": "Compensation"},
                source_clause="S001_C001",
            ),
            GraphNode(
                id=obligation_id,
                label="Obligation",
                properties={"text": "Implement reasonable security practices"},
                source_clause="S001_C001",
            ),
        ],
        relationships=[
            GraphRelationship(source=law_id, target=section_id, type="HAS_SECTION"),
            GraphRelationship(
                source=section_id,
                target=obligation_id,
                type="IMPOSES",
            ),
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


def _load(graph: GraphIR) -> dict[str, int]:
    uri, user, password = _neo4j_auth()
    loader = Neo4jLoader(Neo4jConfig(uri=uri, username=user, password=password))
    loader.connect()
    try:
        return loader.execute(CypherGenerator().generate(graph))
    finally:
        loader.close()


def test_second_ingest_creates_zero_nodes_and_relationships(
    neo4j_driver: Driver,
    sample_graph: GraphIR,
    graph_prefix: str,
) -> None:
    first = _load(sample_graph)
    assert first["nodes_created"] == 3
    assert first["relationships_created"] == 2
    assert _counts(neo4j_driver, graph_prefix) == (3, 2)

    second = _load(sample_graph)
    assert second["nodes_created"] == 0
    assert second["relationships_created"] == 0
    assert _counts(neo4j_driver, graph_prefix) == (3, 2)


def test_reingest_updates_properties_without_duplicating(
    neo4j_driver: Driver,
    sample_graph: GraphIR,
    graph_prefix: str,
) -> None:
    _load(sample_graph)
    updated = GraphIR(
        nodes=[
            GraphNode(
                id=node.id,
                label=node.label,
                properties={**node.properties, "title": "Updated compensation"}
                if node.label == "Section"
                else dict(node.properties),
                source_clause=node.source_clause,
            )
            for node in sample_graph.nodes
        ],
        relationships=list(sample_graph.relationships),
    )
    stats = _load(updated)
    assert stats["nodes_created"] == 0
    assert stats["relationships_created"] == 0
    assert _counts(neo4j_driver, graph_prefix) == (3, 2)

    section_id = f"{graph_prefix}sec"
    with neo4j_driver.session() as session:
        title = session.run(
            "MATCH (n {id: $id}) RETURN n.title AS title",
            id=section_id,
        ).single()["title"]
    assert title == "Updated compensation"
