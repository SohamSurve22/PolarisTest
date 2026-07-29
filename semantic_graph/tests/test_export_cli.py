"""Tests for the ``semantic-graph export`` CLI command."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from semantic_graph.cli.main import build_parser, main

# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParser:
    def test_export_subcommand_registered(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["export", "dummy.txt"])
        assert args.command == "export"
        assert hasattr(args, "handler")

    def test_export_with_text_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["export", "--text", "some content"])
        assert args.command == "export"
        assert args.text == "some content"

    def test_export_with_uri(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["export", "dummy.txt", "--uri", "bolt://localhost:9999"],
        )
        assert args.uri == "bolt://localhost:9999"

    def test_export_with_credentials(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["export", "dummy.txt", "--user", "admin", "--password", "secret"],
        )
        assert args.user == "admin"
        assert args.password == "secret"

    def test_uri_defaults_from_env(self) -> None:
        os.environ["NEO4J_URI"] = "bolt://custom:7687"
        parser = build_parser()
        args = parser.parse_args(["export", "dummy.txt"])
        assert args.uri == "bolt://custom:7687"
        del os.environ["NEO4J_URI"]

    def test_user_defaults_from_env(self) -> None:
        os.environ["NEO4J_USER"] = "custom_user"
        parser = build_parser()
        args = parser.parse_args(["export", "dummy.txt"])
        assert args.user == "custom_user"
        del os.environ["NEO4J_USER"]

    def test_password_defaults_from_env(self) -> None:
        os.environ["NEO4J_PASSWORD"] = "env_secret"
        parser = build_parser()
        args = parser.parse_args(["export", "dummy.txt"])
        assert args.password == "env_secret"
        del os.environ["NEO4J_PASSWORD"]

    def test_no_args_shows_help(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_both_path_and_text_fails(self) -> None:
        result = main(["export", "path.txt", "--text", "content"])
        assert result == 2

    def test_neither_path_nor_text_fails(self) -> None:
        result = main(["export"])
        assert result == 2


# ---------------------------------------------------------------------------
# End-to-end flow test (mocked Neo4j)
# ---------------------------------------------------------------------------


class TestExportFlow:
    MOCK_TEXT = (
        "This Privacy Policy describes how Acme Corp collects and processes "
        "your personal data when you use our services. We collect information "
        "such as your name, email address, and browsing activity. Your data is "
        "shared with third-party analytics providers. We retain your personal "
        "information for as long as your account is active. You have the right "
        "to access, correct, and delete your personal data under applicable law."
    )

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_export_from_text_returns_zero(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 10, "relationships_created": 5}

        result = main(["export", "--text", self.MOCK_TEXT])

        assert result == 0
        mock_export.assert_called_once()

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_export_creates_graph_with_nodes_and_rels(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 10, "relationships_created": 5}

        main(["export", "--text", self.MOCK_TEXT])

        graph = mock_export.call_args[0][0]
        assert len(graph.nodes) > 0
        assert len(graph.relationships) > 0

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_export_graph_contains_lawversion_node(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 1, "relationships_created": 0}

        main(["export", "--text", self.MOCK_TEXT])

        graph = mock_export.call_args[0][0]
        labels = {n.label for n in graph.nodes}
        assert "LawVersion" in labels

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_export_graph_contains_clause_nodes(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 10, "relationships_created": 5}

        main(["export", "--text", self.MOCK_TEXT])

        graph = mock_export.call_args[0][0]
        labels = {n.label for n in graph.nodes}
        assert "Clause" in labels

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_export_graph_contains_section_nodes(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 10, "relationships_created": 5}

        main(["export", "--text", self.MOCK_TEXT])

        graph = mock_export.call_args[0][0]
        labels = {n.label for n in graph.nodes}
        assert "Section" in labels or "SubSection" in labels

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_export_graph_has_relationship_types(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 10, "relationships_created": 5}

        main(["export", "--text", self.MOCK_TEXT])

        graph = mock_export.call_args[0][0]
        rel_types = {r.type for r in graph.relationships}
        assert len(rel_types) > 0

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_neo4j_uri_user_password_forwarded(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 10, "relationships_created": 5}
        mock_export.side_effect = lambda g, u, us, p: (
            setattr(mock_export, "_captured_uri", u)
            or setattr(mock_export, "_captured_user", us)
            or setattr(mock_export, "_captured_password", p)
            or {"nodes_created": 10, "relationships_created": 5}
        )

        main([
            "export", "--text", self.MOCK_TEXT,
            "--uri", "bolt://remote:7687",
            "--user", "admin",
            "--password", "s3cret",
        ])

        assert mock_export._captured_uri == "bolt://remote:7687"
        assert mock_export._captured_user == "admin"
        assert mock_export._captured_password == "s3cret"

    @patch("semantic_graph.cli.export_graph._run_document_pipeline")
    def test_export_propagates_pipeline_error(
        self,
        mock_pipeline: MagicMock,
    ) -> None:
        mock_pipeline.side_effect = RuntimeError("pipeline failed")

        result = main(["export", "--text", self.MOCK_TEXT])

        assert result == 1

    def test_export_from_missing_file(self) -> None:
        result = main(["export", "nonexistent_file_xyz.txt"])
        assert result == 1

    def test_export_from_unsupported_extension(self) -> None:
        tmp = Path("test_unsupported.xyz")
        try:
            tmp.write_text("dummy")
            result = main(["export", str(tmp)])
            assert result == 1
        finally:
            tmp.unlink(missing_ok=True)

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_export_from_file_path(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 10, "relationships_created": 5}
        tmp = Path("test_export_cli_temp.txt")
        try:
            tmp.write_text(self.MOCK_TEXT, encoding="utf-8")
            result = main(["export", str(tmp)])
            assert result == 0
            mock_export.assert_called_once()
        finally:
            tmp.unlink(missing_ok=True)

    @patch("semantic_graph.cli.export_graph._export_to_neo4j")
    def test_export_passes_credentials_to_exporter(
        self,
        mock_export: MagicMock,
    ) -> None:
        mock_export.return_value = {"nodes_created": 10, "relationships_created": 5}
        mock_export.side_effect = lambda *args: {"nodes_created": 10, "relationships_created": 5}

        main([
            "export", "--text", self.MOCK_TEXT,
            "--uri", "bolt://cluster:7687",
            "--user", "reader",
            "--password", "pass",
        ])

        call_args = mock_export.call_args
        assert call_args[0][1] == "bolt://cluster:7687"
        assert call_args[0][2] == "reader"
        assert call_args[0][3] == "pass"
