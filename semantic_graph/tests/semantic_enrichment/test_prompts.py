"""Tests for the prompt template module."""

from __future__ import annotations

from semantic_graph.semantic_enrichment.prompts import build_analysis_prompt


class TestBuildAnalysisPrompt:
    def test_returns_system_and_user(self) -> None:
        system, user = build_analysis_prompt("Some clause text.")
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert len(system) > 0
        assert len(user) > 0

    def test_system_prompt_mentions_json(self) -> None:
        system, _ = build_analysis_prompt("text")
        assert "JSON" in system

    def test_user_prompt_contains_clause_text(self) -> None:
        _, user = build_analysis_prompt("Every driver must have a licence.")
        assert "Every driver must have a licence." in user

    def test_user_prompt_contains_obligations_key(self) -> None:
        _, user = build_analysis_prompt("text")
        assert '"obligations"' in user

    def test_user_prompt_contains_schema_fields(self) -> None:
        _, user = build_analysis_prompt("text")
        for field in ("subject", "action", "object", "condition", "exception"):
            assert f'"{field}"' in user

    def test_different_text_gives_different_user_prompt(self) -> None:
        _, user_a = build_analysis_prompt("Clause A.")
        _, user_b = build_analysis_prompt("Clause B.")
        assert user_a != user_b
