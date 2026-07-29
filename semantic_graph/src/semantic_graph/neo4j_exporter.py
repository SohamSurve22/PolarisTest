"""Neo4j persistence layer for the semantic graph.

Converts a ``GraphIR`` into Neo4j nodes and relationships using
parameterised MERGE statements executed inside a managed transaction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from semantic_graph.neo4j_schema import NodeLabel, RelType

if TYPE_CHECKING:
    from neo4j import Driver, Session, Transaction

_VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Default mapping from GraphIR labels to Neo4j node labels.
_DEFAULT_LABEL_MAP: dict[str, str] = {
    "LawVersion": NodeLabel.DOCUMENT,
    "Act": NodeLabel.ACT,
    "Chapter": NodeLabel.CHAPTER,
    "Part": NodeLabel.PART,
    "Section": NodeLabel.SECTION,
    "SubSection": NodeLabel.SECTION,
    "Clause": NodeLabel.CLAUSE,
    "Entity": NodeLabel.ENTITY,
    "UnresolvedReference": NodeLabel.UNRESOLVED_REFERENCE,
}

# Default mapping from GraphIR relationship types to Neo4j relationship types.
_DEFAULT_REL_MAP: dict[str, str] = {
    "HAS_CHAPTER": RelType.CONTAINS,
    "HAS_SECTION": RelType.CONTAINS,
    "HAS_SUBSECTION": RelType.CONTAINS,
    "HAS_CLAUSE": RelType.HAS_CLAUSE,
    "REFERENCES": RelType.REFERENCES,
    "UNRESOLVED_REFERENCE": RelType.REFERS_TO,
}


@dataclass
class _CypherOp:
    """A single parameterised Cypher operation ready for execution."""

    query: str
    parameters: dict[str, Any]


_NODE_TMPL = "MERGE (n:{label} {{id: $n_id}}) SET n += $n_props"
_REL_TMPL = (
    "MATCH (source {{id: $source_id}}) "
    "MATCH (target {{id: $target_id}}) "
    "MERGE (source)-[r:{rel_type}]->(target) "
    "SET r += $r_props"
)


class Neo4jExporter:
    """Exports a ``GraphIR`` into a Neo4j database.

    The exporter uses label and relationship-type mapping tables so that
    GraphIR labels (e.g. ``"LawVersion"``) become canonical Neo4j labels
    (e.g. ``"Document"``).  Both mappings can be overridden via constructor
    injection.

    All Cypher uses ``MERGE`` to guarantee idempotency: re-exporting
    the same ``GraphIR`` will not create duplicate nodes or relationships.
    """

    def __init__(
        self,
        driver: Driver,
        label_map: dict[str, str] | None = None,
        rel_type_map: dict[str, str] | None = None,
    ) -> None:
        """Initialise the exporter.

        Args:
            driver: An open ``neo4j.Driver`` instance connected to the
                target database.
            label_map: Optional override for the GraphIR-label → Neo4j-label
                mapping.  Defaults to ``_DEFAULT_LABEL_MAP``.
            rel_type_map: Optional override for the GraphIR-relationship-type
                → Neo4j-relationship-type mapping.  Defaults to
                ``_DEFAULT_REL_MAP``.
        """
        self._driver = driver
        self._label_map = label_map or dict(_DEFAULT_LABEL_MAP)
        self._rel_type_map = rel_type_map or dict(_DEFAULT_REL_MAP)

    def export(self, graph: GraphIR) -> dict[str, int]:
        """Persist the ``GraphIR`` into Neo4j.

        All operations run inside a single managed transaction.  Existing
        nodes are matched by ``id``; relationships are matched by
        source + target + type.

        Args:
            graph: The graph intermediate representation to persist.

        Returns:
            A dict with ``"nodes_created"`` and ``"relationships_created"``
            keys reflecting the counters returned by Neo4j.
        """
        if not graph.nodes:
            return {"nodes_created": 0, "relationships_created": 0}

        node_ops = _build_node_ops(graph.nodes, self._label_map)
        rel_ops = _build_rel_ops(graph.relationships, self._rel_type_map)
        all_ops = node_ops + rel_ops

        with self._driver.session() as session:
            _explain(session, all_ops)
            nodes_created, relationships_created = session.execute_write(
                _transaction_fn(node_ops, rel_ops),
            )

        return {
            "nodes_created": nodes_created,
            "relationships_created": relationships_created,
        }


# ---------------------------------------------------------------------------
# Cypher helpers
# ---------------------------------------------------------------------------


def _merge_node_query(node: GraphNode, neo4j_label: str) -> _CypherOp:
    """Build a parameterised MERGE statement for a single node."""
    props: dict[str, Any] = dict(node.properties)
    props["id"] = node.id
    if node.source_clause is not None:
        props["source_clause"] = node.source_clause
    label = _sanitise(neo4j_label, "node label")
    return _CypherOp(
        query=_NODE_TMPL.format(label=label),
        parameters={"n_id": node.id, "n_props": props},
    )


def _merge_rel_query(rel: GraphRelationship, neo4j_type: str) -> _CypherOp:
    """Build a parameterised MERGE statement for a single relationship."""
    rtype = _sanitise(neo4j_type, "relationship type")
    return _CypherOp(
        query=_REL_TMPL.format(rel_type=rtype),
        parameters={
            "source_id": rel.source,
            "target_id": rel.target,
            "r_props": dict(rel.properties),
        },
    )


def _build_node_ops(
    nodes: list[GraphNode],
    label_map: dict[str, str],
) -> list[_CypherOp]:
    """Generate MERGE operations for every node in the graph."""
    return [_merge_node_query(n, label_map.get(n.label, n.label)) for n in nodes]


def _build_rel_ops(
    relationships: list[GraphRelationship],
    rel_type_map: dict[str, str],
) -> list[_CypherOp]:
    """Generate MERGE operations for every relationship in the graph."""
    return [
        _merge_rel_query(r, rel_type_map.get(r.type, r.type))
        for r in relationships
    ]


def _explain(session: Session, ops: list[_CypherOp]) -> None:
    """Run EXPLAIN on every operation to validate syntax early."""
    for op in ops:
        explain_query = f"EXPLAIN {op.query}"
        session.run(explain_query, op.parameters).consume()


def _transaction_fn(
    node_ops: list[_CypherOp],
    rel_ops: list[_CypherOp],
) -> Any:
    """Return a callable suitable for ``session.execute_write``."""

    def _run(tx: Transaction) -> tuple[int, int]:
        nodes_created = 0
        rels_created = 0
        for op in node_ops:
            summary = tx.run(op.query, op.parameters).consume()
            nodes_created += summary.counters.nodes_created
        for op in rel_ops:
            summary = tx.run(op.query, op.parameters).consume()
            rels_created += summary.counters.relationships_created
        return nodes_created, rels_created

    return _run


def _sanitise(value: str, kind: str) -> str:
    """Validate that *value* is a safe Cypher identifier."""
    if not _VALID_IDENTIFIER.match(value):
        raise ValueError(
            f"Invalid {kind} '{value}': must match {_VALID_IDENTIFIER.pattern}.",
        )
    return value
