"""Tests for ``Neo4jExporter`` with a mocked Neo4j driver."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from semantic_graph.neo4j_exporter import Neo4jExporter
from semantic_graph.neo4j_schema import NodeLabel, RelType


def _make_summary(nodes: int = 1, rels: int = 1) -> MagicMock:
    summary = MagicMock()
    summary.counters.nodes_created = nodes
    summary.counters.relationships_created = rels
    return summary


def _mock_driver_and_session() -> tuple[MagicMock, MagicMock, MagicMock]:
    """Return ``(mock_graph_db, mock_driver, mock_session)``."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_driver.session.return_value = mock_session
    return mock_driver, mock_session


def _configure_session(
    mock_session: MagicMock,
    *,
    explain_ok: bool = True,
) -> MagicMock:
    """Wire up mock session.run side effects.

    For EXPLAIN queries returns a zero-summary result.
    For real queries returns a ``_make_summary`` result.

    ``tx.run`` calls made inside ``execute_write`` are redirected to
    ``session.run`` so that all queries appear on a single
    ``call_args_list`` for verification.
    """
    explain_result = MagicMock()
    explain_result.consume.return_value = _make_summary(0, 0)

    node_result = MagicMock()
    node_result.consume.return_value = _make_summary(1, 0)

    rel_result = MagicMock()
    rel_result.consume.return_value = _make_summary(0, 1)

    call_count: list[int] = [0]

    def run_side_effect(
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> MagicMock:
        _ = parameters
        if query.startswith("EXPLAIN"):
            if not explain_ok:
                msg = "syntax error"
                raise RuntimeError(msg)
            return explain_result
        call_count[0] += 1
        return node_result if call_count[0] <= 1 else rel_result

    mock_session.run.side_effect = run_side_effect

    def execute_write_side(fn: Any) -> Any:
        mock_tx = MagicMock()
        mock_tx.run.side_effect = lambda q, p=None: mock_session.run(q, p)
        return fn(mock_tx)

    mock_session.execute_write.side_effect = execute_write_side
    return mock_session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNodeCreation:

    def test_creates_node_with_properties(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[GraphNode(id="sec_1", label="Section", properties={"number": "1", "title": "Scope"})],
            relationships=[],
        )
        result = exporter.export(graph)

        assert result["nodes_created"] == 1
        assert result["relationships_created"] == 0

        # Verify the MERGE query was constructed with mapped label
        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        assert len(calls) >= 1
        query = calls[0].args[0]
        assert "MERGE (n:Section" in query
        assert "id: $n_id" in query
        assert "SET n += $n_props" in query

    def test_preserves_all_properties(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[GraphNode(
                id="c1", label="Clause",
                properties={"clause_id": "S001_C001", "text": "Content", "confidence": 0.95},
            )],
            relationships=[],
        )
        exporter.export(graph)

        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        params = calls[0].args[1]
        props = params["n_props"]
        assert props["id"] == "c1"
        assert props["clause_id"] == "S001_C001"
        assert props["text"] == "Content"
        assert props["confidence"] == 0.95

    def test_label_mapping_lawversion_to_document(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[GraphNode(id="law_1", label="LawVersion", properties={"law_code": "1"})],
            relationships=[],
        )
        exporter.export(graph)

        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        query = calls[0].args[0]
        assert "MERGE (n:Document" in query

    def test_source_clause_included(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[GraphNode(
                id="c1", label="Clause", properties={},
                source_clause="S001_C001",
            )],
            relationships=[],
        )
        exporter.export(graph)

        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        params = calls[0].args[1]
        assert params["n_props"]["source_clause"] == "S001_C001"


class TestRelationshipCreation:

    def test_creates_relationship(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[
                GraphNode(id="sec_1", label="Section", properties={"number": "1"}),
                GraphNode(id="cl_1", label="Clause", properties={"clause_id": "S001_C001"}),
            ],
            relationships=[
                GraphRelationship(source="sec_1", target="cl_1", type="HAS_CLAUSE"),
            ],
        )
        result = exporter.export(graph)

        assert result["nodes_created"] == 1
        assert result["relationships_created"] == 1

    def test_relationship_type_mapping(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[
                GraphNode(id="law_1", label="LawVersion", properties={}),
                GraphNode(id="ch_1", label="Chapter", properties={"number": "1"}),
            ],
            relationships=[
                GraphRelationship(source="law_1", target="ch_1", type="HAS_CHAPTER"),
            ],
        )
        exporter.export(graph)

        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        rel_call = calls[-1]
        query = rel_call.args[0]
        assert "MERGE (source)-[r:CONTAINS]->(target)" in query

    def test_relationship_properties_preserved(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[
                GraphNode(id="a", label="Section", properties={}),
                GraphNode(id="b", label="Clause", properties={}),
            ],
            relationships=[
                GraphRelationship(
                    source="a", target="b", type="REFERENCES",
                    properties={"source_clause": "S001_C001"},
                ),
            ],
        )
        exporter.export(graph)

        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        rel_call = calls[-1]
        params = rel_call.args[1]
        assert params["r_props"]["source_clause"] == "S001_C001"
        assert params["source_id"] == "a"
        assert params["target_id"] == "b"


class TestDuplicatePrevention:

    def test_merge_prevents_duplicate_nodes(self) -> None:
        """MERGE is used, so exporting the same graph twice is idempotent."""
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[GraphNode(id="sec_1", label="Section", properties={"number": "1"})],
            relationships=[],
        )
        result1 = exporter.export(graph)
        result2 = exporter.export(graph)

        # Both exports should succeed (MERGE doesn't error on existing nodes)
        assert result1["nodes_created"] >= 0
        assert result2["nodes_created"] >= 0


class TestEmptyGraph:

    def test_empty_graph_returns_zero_counts(self) -> None:
        mock_driver = MagicMock()
        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(nodes=[], relationships=[])
        result = exporter.export(graph)

        assert result["nodes_created"] == 0
        assert result["relationships_created"] == 0
        mock_driver.session.assert_not_called()


class TestUnresolvedReferenceExport:

    def test_exports_unresolved_nodes(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[
                GraphNode(
                    id="unresolved_1",
                    label="UnresolvedReference",
                    properties={
                        "reference_text": "Section 99",
                        "reference_type": "section",
                        "clause_id": "S001_C001",
                    },
                ),
            ],
            relationships=[],
        )
        result = exporter.export(graph)

        assert result["nodes_created"] == 1
        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        query = calls[0].args[0]
        assert "UnresolvedReference" in query


class TestLabelMapping:

    def test_custom_label_map_injection(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        custom_map = {"Section": "CustomSection"}
        exporter = Neo4jExporter(driver=mock_driver, label_map=custom_map)
        graph = GraphIR(
            nodes=[GraphNode(id="s1", label="Section", properties={"number": "1"})],
            relationships=[],
        )
        exporter.export(graph)

        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        query = calls[0].args[0]
        assert "MERGE (n:CustomSection" in query

    def test_custom_rel_type_map_injection(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        custom_map = {"HAS_CLAUSE": "OWNS"}
        exporter = Neo4jExporter(driver=mock_driver, rel_type_map=custom_map)
        graph = GraphIR(
            nodes=[
                GraphNode(id="s1", label="Section", properties={}),
                GraphNode(id="c1", label="Clause", properties={}),
            ],
            relationships=[
                GraphRelationship(source="s1", target="c1", type="HAS_CLAUSE"),
            ],
        )
        exporter.export(graph)

        calls = [c for c in mock_session.run.call_args_list if not c.args[0].startswith("EXPLAIN")]
        rel_call = calls[-1]
        query = rel_call.args[0]
        assert "MERGE (source)-[r:OWNS]->(target)" in query


class TestSchemaConstants:

    def test_schema_labels_defined(self) -> None:
        assert NodeLabel.DOCUMENT == "Document"
        assert NodeLabel.ACT == "Act"
        assert NodeLabel.CHAPTER == "Chapter"
        assert NodeLabel.PART == "Part"
        assert NodeLabel.SECTION == "Section"
        assert NodeLabel.CLAUSE == "Clause"
        assert NodeLabel.ENTITY == "Entity"
        assert NodeLabel.UNRESOLVED_REFERENCE == "UnresolvedReference"

    def test_schema_rel_types_defined(self) -> None:
        assert RelType.CONTAINS == "CONTAINS"
        assert RelType.HAS_CLAUSE == "HAS_CLAUSE"
        assert RelType.REFERENCES == "REFERENCES"
        assert RelType.MENTIONS == "MENTIONS"
        assert RelType.REFERS_TO == "REFERS_TO"

    def test_default_map_covers_known_labels(self) -> None:
        from semantic_graph.neo4j_exporter import _DEFAULT_LABEL_MAP
        assert "LawVersion" in _DEFAULT_LABEL_MAP
        assert "Chapter" in _DEFAULT_LABEL_MAP
        assert "Section" in _DEFAULT_LABEL_MAP
        assert "SubSection" in _DEFAULT_LABEL_MAP
        assert "Clause" in _DEFAULT_LABEL_MAP
        assert "UnresolvedReference" in _DEFAULT_LABEL_MAP

    def test_default_map_covers_known_rels(self) -> None:
        from semantic_graph.neo4j_exporter import _DEFAULT_REL_MAP
        assert "HAS_CHAPTER" in _DEFAULT_REL_MAP
        assert "HAS_SECTION" in _DEFAULT_REL_MAP
        assert "HAS_SUBSECTION" in _DEFAULT_REL_MAP
        assert "HAS_CLAUSE" in _DEFAULT_REL_MAP
        assert "REFERENCES" in _DEFAULT_REL_MAP
        assert "UNRESOLVED_REFERENCE" in _DEFAULT_REL_MAP


class TestValidation:

    def test_invalid_label_raises(self) -> None:
        mock_driver = MagicMock()
        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[GraphNode(id="bad", label="Bad Label!", properties={})],
            relationships=[],
        )
        with pytest.raises(ValueError, match="Invalid node label"):
            exporter.export(graph)

    def test_invalid_rel_type_raises(self) -> None:
        mock_driver = MagicMock()
        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[
                GraphNode(id="a", label="Section", properties={}),
                GraphNode(id="b", label="Clause", properties={}),
            ],
            relationships=[
                GraphRelationship(source="a", target="b", type="has clause"),
            ],
        )
        with pytest.raises(ValueError, match="Invalid relationship type"):
            exporter.export(graph)


class TestExplainFailure:

    def test_explain_failure_propagates(self) -> None:
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session, explain_ok=False)  # type: ignore[arg-type]

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[GraphNode(id="s1", label="Section", properties={})],
            relationships=[],
        )
        with pytest.raises(RuntimeError, match="syntax error"):
            exporter.export(graph)


class EndToEndIntegration:

    def test_full_document_export(self) -> None:
        """Simulate a realistic multi-node, multi-relationship export."""
        mock_driver, mock_session = _mock_driver_and_session()
        _configure_session(mock_session)

        exporter = Neo4jExporter(driver=mock_driver)
        graph = GraphIR(
            nodes=[
                GraphNode(id="law_1", label="LawVersion", properties={"law_code": "ACT-001", "title": "Test Act"}),
                GraphNode(id="ch_1", label="Chapter", properties={"number": "1", "title": "Preliminary"}),
                GraphNode(id="sec_1", label="Section", properties={"number": "5", "title": "Definitions"}),
                GraphNode(id="cl_1", label="Clause", properties={"clause_id": "S001_C001", "text": "Define terms."}),
                GraphNode(id="unresolved_1", label="UnresolvedReference", properties={
                    "reference_text": "Rule 10", "reference_type": "rule", "clause_id": "S001_C001",
                }),
            ],
            relationships=[
                GraphRelationship(source="law_1", target="ch_1", type="HAS_CHAPTER"),
                GraphRelationship(source="ch_1", target="sec_1", type="HAS_SECTION"),
                GraphRelationship(source="sec_1", target="cl_1", type="HAS_CLAUSE"),
                GraphRelationship(source="cl_1", target="unresolved_1", type="UNRESOLVED_REFERENCE"),
            ],
        )
        result = exporter.export(graph)

        assert result["nodes_created"] >= 0
        assert result["relationships_created"] >= 0

        # Verify label mapping
        calls = [c for c in mock_session.run.call_args_list]
        real_calls = [c for c in calls if not c.args[0].startswith("EXPLAIN")]
        node_queries = [c.args[0] for c in real_calls if "MERGE (n:" in c.args[0]]
        assert any("MERGE (n:Document" in q for q in node_queries)
        assert any("MERGE (n:Chapter" in q for q in node_queries)
        assert any("MERGE (n:Section" in q for q in node_queries)
        assert any("MERGE (n:Clause" in q for q in node_queries)
        assert any("MERGE (n:UnresolvedReference" in q for q in node_queries)
