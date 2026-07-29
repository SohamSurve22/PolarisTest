"""Tests for the semantic enrichment graph stage."""

from __future__ import annotations

from unittest.mock import MagicMock

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from semantic_graph.semantic_enrichment.enrichment_models import ClauseMeaning, Obligation
from semantic_graph.semantic_enrichment.semantic_enrichment_stage import (
    SemanticEnrichmentStage,
    _find_clause_nodes,
)

# ---------------------------------------------------------------------------
# _find_clause_nodes
# ---------------------------------------------------------------------------


class TestFindClauseNodes:
    def test_returns_clause_nodes_only(self) -> None:
        nodes = [
            GraphNode(id="doc_1", label="LawVersion"),
            GraphNode(id="sec_1", label="Section"),
            GraphNode(id="cl_1", label="Clause"),
            GraphNode(id="cl_2", label="Clause"),
        ]
        result = _find_clause_nodes(nodes)
        assert len(result) == 2
        assert result[0].id == "cl_1"
        assert result[1].id == "cl_2"

    def test_empty_when_no_clauses(self) -> None:
        nodes = [
            GraphNode(id="doc_1", label="LawVersion"),
            GraphNode(id="sec_1", label="Section"),
        ]
        assert _find_clause_nodes(nodes) == []

    def test_empty_when_empty_list(self) -> None:
        assert _find_clause_nodes([]) == []


# ---------------------------------------------------------------------------
# SemanticEnrichmentStage
# ---------------------------------------------------------------------------


def _mock_analyzer(
    *clause_meanings: ClauseMeaning,
) -> MagicMock:
    analyzer = MagicMock()
    analyzer.analyze.side_effect = list(clause_meanings)
    return analyzer


class TestSemanticEnrichmentStage:
    def test_enriches_single_clause(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(
                    id="cl_1", label="Clause",
                    properties={"text": "Driver must possess licence."},
                ),
            ],
            relationships=[],
        )
        meaning = ClauseMeaning(
            clause_id="cl_1",
            obligations=[Obligation(subject="driver", action="possess", object="licence")],
        )
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(meaning))

        result = stage.process(graph)

        assert len(result.nodes) == 2
        assert len(result.relationships) == 1
        assert result.nodes[0].id == "cl_1"
        assert result.nodes[1].label == "Obligation"
        assert result.relationships[0].type == "HAS_OBLIGATION"
        assert result.relationships[0].source == "cl_1"

    def test_enriches_multiple_clauses(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="cl_1", label="Clause", properties={"text": "First clause."}),
                GraphNode(id="cl_2", label="Clause", properties={"text": "Second clause."}),
            ],
            relationships=[],
        )
        meanings = [
            ClauseMeaning(clause_id="cl_1", obligations=[Obligation(subject="s1", action="a1", object="o1")]),  # noqa: E501
            ClauseMeaning(clause_id="cl_2", obligations=[Obligation(subject="s2", action="a2", object="o2")]),  # noqa: E501
        ]
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(*meanings))

        result = stage.process(graph)

        assert len(result.nodes) == 4
        assert len(result.relationships) == 2
        assert result.nodes[2].label == "Obligation"
        assert result.nodes[3].label == "Obligation"

    def test_multiple_obligations_per_clause(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="cl_1", label="Clause", properties={"text": "Do X and Y."}),
            ],
            relationships=[],
        )
        meaning = ClauseMeaning(
            clause_id="cl_1",
            obligations=[
                Obligation(subject="s", action="do_x", object="x"),
                Obligation(subject="s", action="do_y", object="y"),
            ],
        )
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(meaning))

        result = stage.process(graph)

        assert len(result.nodes) == 3
        assert len(result.relationships) == 2

    def test_clause_with_no_obligations_unchanged(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="cl_1", label="Clause", properties={"text": "Definitions apply."}),
            ],
            relationships=[],
        )
        meaning = ClauseMeaning(clause_id="cl_1", obligations=[])
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(meaning))

        result = stage.process(graph)

        assert len(result.nodes) == 1
        assert len(result.relationships) == 0

    def test_empty_graph_unchanged(self) -> None:
        graph = GraphIR(nodes=[], relationships=[])
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer())

        result = stage.process(graph)

        assert result.nodes == []
        assert result.relationships == []

    def test_no_clause_nodes_unchanged(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="law_1", label="LawVersion"),
                GraphNode(id="sec_1", label="Section"),
            ],
            relationships=[],
        )
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer())

        result = stage.process(graph)

        assert len(result.nodes) == 2
        assert len(result.relationships) == 0

    def test_original_nodes_preserved(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="doc_1", label="LawVersion", properties={"title": "GDPR"}),
                GraphNode(id="cl_1", label="Clause", properties={"text": "Process data lawfully."}),
            ],
            relationships=[
                GraphRelationship(source="doc_1", target="cl_1", type="CONTAINS"),
            ],
        )
        meaning = ClauseMeaning(
            clause_id="cl_1",
            obligations=[Obligation(subject="controller", action="process", object="data lawfully")],  # noqa: E501
        )
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(meaning))

        result = stage.process(graph)

        assert result.nodes[0].id == "doc_1"
        assert result.nodes[0].properties["title"] == "GDPR"
        assert result.relationships[0].type == "CONTAINS"
        assert result.relationships[0].source == "doc_1"

    def test_obligation_properties_set_correctly(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(
                    id="cl_1", label="Clause",
                    properties={"text": "Driver must possess a licence while driving, unless exempt."},  # noqa: E501
                ),
            ],
            relationships=[],
        )
        meaning = ClauseMeaning(
            clause_id="cl_1",
            obligations=[Obligation(
                subject="driver",
                action="possess",
                object="licence",
                condition="while driving",
                exception="unless exempt",
            )],
        )
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(meaning))

        result = stage.process(graph)
        ob_node = result.nodes[1]

        assert ob_node.properties["subject"] == "driver"
        assert ob_node.properties["action"] == "possess"
        assert ob_node.properties["object"] == "licence"
        assert ob_node.properties["condition"] == "while driving"
        assert ob_node.properties["exception"] == "unless exempt"

    def test_obligation_id_format(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="cl_3.1", label="Clause", properties={"text": "Do something."}),
            ],
            relationships=[],
        )
        meaning = ClauseMeaning(
            clause_id="cl_3.1",
            obligations=[Obligation(subject="s", action="a", object="o")],
        )
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(meaning))

        result = stage.process(graph)
        ob_node = result.nodes[1]

        assert ob_node.id == "obl_cl_3.1_0"

    def test_multiple_obligations_increment_index(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="cl_1", label="Clause", properties={"text": "Do X and Y."}),
            ],
            relationships=[],
        )
        meaning = ClauseMeaning(
            clause_id="cl_1",
            obligations=[
                Obligation(subject="s", action="do_x", object="x"),
                Obligation(subject="s", action="do_y", object="y"),
            ],
        )
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(meaning))

        result = stage.process(graph)
        assert result.nodes[1].id == "obl_cl_1_0"
        assert result.nodes[2].id == "obl_cl_1_1"

    def test_analyzer_called_per_clause(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="c1", label="Clause", properties={"text": "T1"}),
                GraphNode(id="c2", label="Clause", properties={"text": "T2"}),
            ],
            relationships=[],
        )
        analyzer = MagicMock()
        analyzer.analyze.side_effect = [
            ClauseMeaning("c1", [Obligation("s", "a", "o")]),
            ClauseMeaning("c2", [Obligation("s", "a", "o")]),
        ]
        stage = SemanticEnrichmentStage(analyzer=analyzer)

        stage.process(graph)

        assert analyzer.analyze.call_count == 2
        analyzer.analyze.assert_any_call("T1", "c1")
        analyzer.analyze.assert_any_call("T2", "c2")

    def test_missing_text_property_empty_string(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="cl_1", label="Clause", properties={}),
            ],
            relationships=[],
        )
        analyzer = MagicMock()
        analyzer.analyze.return_value = ClauseMeaning("cl_1", [])
        stage = SemanticEnrichmentStage(analyzer=analyzer)

        result = stage.process(graph)

        analyzer.analyze.assert_called_once_with("", "cl_1")
        assert len(result.nodes) == 1

    def test_non_clause_nodes_ignored(self) -> None:
        graph = GraphIR(
            nodes=[
                GraphNode(id="doc", label="LawVersion"),
                GraphNode(id="cl_1", label="Clause", properties={"text": "Obligation text."}),
                GraphNode(id="ent", label="Entity"),
            ],
            relationships=[],
        )
        meaning = ClauseMeaning(
            clause_id="cl_1",
            obligations=[Obligation(subject="s", action="a", object="o")],
        )
        stage = SemanticEnrichmentStage(analyzer=_mock_analyzer(meaning))

        result = stage.process(graph)

        assert len(result.nodes) == 4
        assert result.nodes[0].id == "doc"
        assert result.nodes[2].id == "ent"
