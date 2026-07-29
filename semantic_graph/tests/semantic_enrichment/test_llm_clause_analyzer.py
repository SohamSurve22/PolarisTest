"""Tests for the LLM-powered clause analyzer."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from semantic_graph.semantic_enrichment.enrichment_models import ClauseMeaning
from semantic_graph.semantic_enrichment.llm_clause_analyzer import (
    LLMClauseAnalyzer,
    _build_clause_meaning,
    _build_obligation,
    _parse_response,
)

# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------


class TestParseResponse:
    def test_parses_valid_json(self) -> None:
        raw = json.dumps({"obligations": [{"subject": "x", "action": "y", "object": "z"}]})
        result = _parse_response(raw)
        assert result["obligations"][0]["subject"] == "x"

    def test_strips_whitespace(self) -> None:
        result = _parse_response("  {\"obligations\": []}  ")
        assert result["obligations"] == []

    def test_raises_on_empty(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            _parse_response("")

    def test_raises_on_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            _parse_response("   \n  ")

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            _parse_response("not json")

    def test_raises_on_non_object(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            _parse_response("[1, 2, 3]")

    def test_raises_on_missing_obligations(self) -> None:
        with pytest.raises(ValueError, match="'obligations' array"):
            _parse_response("{}")

    def test_raises_on_non_list_obligations(self) -> None:
        with pytest.raises(ValueError, match="'obligations' array"):
            _parse_response('{"obligations": "not a list"}')


# ---------------------------------------------------------------------------
# _build_obligation
# ---------------------------------------------------------------------------


class TestBuildObligation:
    def test_full_fields(self) -> None:
        ob = _build_obligation({
            "subject": "driver",
            "action": "possess",
            "object": "licence",
            "condition": "operating vehicle",
            "exception": "learner permit",
        })
        assert ob.subject == "driver"
        assert ob.action == "possess"
        assert ob.object == "licence"
        assert ob.condition == "operating vehicle"
        assert ob.exception == "learner permit"

    def test_minimal_fields(self) -> None:
        ob = _build_obligation({"subject": "x", "action": "y", "object": "z"})
        assert ob.subject == "x"
        assert ob.action == "y"
        assert ob.object == "z"
        assert ob.condition is None
        assert ob.exception is None

    def test_null_condition_exception(self) -> None:
        ob = _build_obligation({
            "subject": "x",
            "action": "y",
            "object": "z",
            "condition": None,
            "exception": None,
        })
        assert ob.condition is None
        assert ob.exception is None

    def test_empty_strings_become_none(self) -> None:
        ob = _build_obligation({
            "subject": "x",
            "action": "y",
            "object": "z",
            "condition": "",
            "exception": "",
        })
        assert ob.condition is None
        assert ob.exception is None

    def test_raises_on_non_dict(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            _build_obligation("not a dict")

    def test_raises_on_non_string_subject(self) -> None:
        with pytest.raises(ValueError, match="'subject' must be a string"):
            _build_obligation({"subject": 123, "action": "y", "object": "z"})

    def test_raises_on_non_string_action(self) -> None:
        with pytest.raises(ValueError, match="'action' must be a string"):
            _build_obligation({"subject": "x", "action": [], "object": "z"})

    def test_raises_on_non_string_object(self) -> None:
        with pytest.raises(ValueError, match="'object' must be a string"):
            _build_obligation({"subject": "x", "action": "y", "object": 42})

    def test_raises_on_non_string_condition(self) -> None:
        with pytest.raises(ValueError, match="'condition' must be a string or null"):
            _build_obligation({
                "subject": "x",
                "action": "y",
                "object": "z",
                "condition": True,
            })


# ---------------------------------------------------------------------------
# _build_clause_meaning
# ---------------------------------------------------------------------------


class TestBuildClauseMeaning:
    def test_single_obligation(self) -> None:
        data: dict[str, Any] = {"obligations": [{"subject": "s", "action": "a", "object": "o"}]}
        cm = _build_clause_meaning("c1", data)
        assert cm.clause_id == "c1"
        assert len(cm.obligations) == 1
        assert cm.obligations[0].subject == "s"

    def test_multiple_obligations(self) -> None:
        data: dict[str, Any] = {
            "obligations": [
                {"subject": "s1", "action": "a1", "object": "o1"},
                {"subject": "s2", "action": "a2", "object": "o2"},
            ],
        }
        cm = _build_clause_meaning("c2", data)
        assert len(cm.obligations) == 2

    def test_empty_obligations(self) -> None:
        data: dict[str, Any] = {"obligations": []}
        cm = _build_clause_meaning("c3", data)
        assert cm.clause_id == "c3"
        assert cm.obligations == []


# ---------------------------------------------------------------------------
# LLMClauseAnalyzer (mocked client)
# ---------------------------------------------------------------------------


def _mock_client(response: str) -> MagicMock:
    client = MagicMock()
    client.generate.return_value = response
    return client


class TestLLMClauseAnalyzer:
    def test_analyze_returns_clause_meaning(self) -> None:
        raw = json.dumps({
            "obligations": [
                {"subject": "driver", "action": "possess", "object": "licence"},
            ],
        })
        analyzer = LLMClauseAnalyzer(client=_mock_client(raw))

        result = analyzer.analyze("Every driver shall possess a licence.", "clause_1")

        assert isinstance(result, ClauseMeaning)
        assert result.clause_id == "clause_1"
        assert len(result.obligations) == 1

    def test_analyze_multiple_obligations(self) -> None:
        raw = json.dumps({
            "obligations": [
                {"subject": "controller", "action": "obtain", "object": "consent"},
                {"subject": "controller", "action": "notify", "object": "board"},
            ],
        })
        analyzer = LLMClauseAnalyzer(client=_mock_client(raw))

        result = analyzer.analyze("The controller must obtain consent and notify the board.", "c1")

        assert len(result.obligations) == 2

    def test_empty_obligation_response(self) -> None:
        raw = json.dumps({"obligations": []})
        analyzer = LLMClauseAnalyzer(client=_mock_client(raw))

        result = analyzer.analyze("This clause defines terms.", "c1")

        assert result.obligations == []

    def test_analyzer_invokes_client_with_prompts(self) -> None:
        client = _mock_client(json.dumps({"obligations": []}))
        analyzer = LLMClauseAnalyzer(client=client)

        analyzer.analyze("Some clause text.", "c1")

        assert client.generate.called
        system, user = client.generate.call_args[0]
        assert "JSON" in system
        assert "Some clause text." in user

    def test_invalid_json_raises(self) -> None:
        analyzer = LLMClauseAnalyzer(client=_mock_client("not json"))

        with pytest.raises(ValueError, match="Invalid JSON"):
            analyzer.analyze("text", "c1")

    def test_clause_id_preserved_in_output(self) -> None:
        raw = json.dumps({"obligations": [{"subject": "s", "action": "a", "object": "o"}]})
        analyzer = LLMClauseAnalyzer(client=_mock_client(raw))

        result = analyzer.analyze("text", "my_clause_42")

        assert result.clause_id == "my_clause_42"
