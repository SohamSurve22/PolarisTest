"""Semantic enrichment stage — enriches a GraphIR with clause meanings.

This stage iterates every ``Clause`` node in the graph, runs a
``ClauseAnalyzer`` on each clause's text (via a ``source_clause`` or
``id`` reference), and attaches ``Obligation`` nodes with
``HAS_OBLIGATION`` relationships back to the source clause.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from semantic_graph.semantic_enrichment.clause_analyzer import ClauseAnalyzer

if TYPE_CHECKING:
    from collections.abc import Sequence


class SemanticEnrichmentStage:
    """Enriches a ``GraphIR`` with clause-level semantic meaning.

    The stage identifies ``Clause`` nodes in the graph, runs the injected
    ``ClauseAnalyzer`` on each one, and adds ``Obligation`` nodes +
    ``HAS_OBLIGATION`` relationships to the graph.

    Args:
        analyzer: The ``ClauseAnalyzer`` to use for extraction.
    """

    def __init__(self, analyzer: ClauseAnalyzer) -> None:
        self._analyzer = analyzer

    def process(self, graph: GraphIR) -> GraphIR:
        """Enrich the graph with obligation nodes and relationships.

        Args:
            graph: The input ``GraphIR`` (preserved, not mutated).

        Returns:
            A new ``GraphIR`` containing all original nodes/relationships
            plus any extracted ``Obligation`` nodes and
            ``HAS_OBLIGATION`` relationships.
        """
        clause_nodes = _find_clause_nodes(graph.nodes)
        if not clause_nodes:
            return graph

        obligation_nodes: list[GraphNode] = []
        obligation_rels: list[GraphRelationship] = []
        obligation_index = 0

        for clause in clause_nodes:
            clause_id = clause.id
            clause_text = clause.properties.get("text", "")

            meaning = self._analyzer.analyze(clause_text, clause_id)
            if not meaning.obligations:
                continue

            for ob in meaning.obligations:
                obligation_id = f"obl_{clause_id}_{obligation_index}"
                obligation_index += 1
                obligation_nodes.append(
                    GraphNode(
                        id=obligation_id,
                        label="Obligation",
                        properties={
                            "subject": ob.subject,
                            "action": ob.action,
                            "object": ob.object,
                            "condition": ob.condition or "",
                            "exception": ob.exception or "",
                        },
                    ),
                )
                obligation_rels.append(
                    GraphRelationship(
                        source=clause_id,
                        target=obligation_id,
                        type="HAS_OBLIGATION",
                    ),
                )

        return GraphIR(
            nodes=list(graph.nodes) + obligation_nodes,
            relationships=list(graph.relationships) + obligation_rels,
        )


def _find_clause_nodes(
    nodes: Sequence[GraphNode],
) -> list[GraphNode]:
    """Return all nodes whose label is ``"Clause"``."""
    return [n for n in nodes if n.label == "Clause"]
