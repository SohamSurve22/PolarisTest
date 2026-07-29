"""Tests for the enrichment data models."""

from __future__ import annotations

from semantic_graph.semantic_enrichment.enrichment_models import ClauseMeaning, Obligation


class TestObligation:
    def test_default_construction(self) -> None:
        ob = Obligation()
        assert ob.subject == ""
        assert ob.action == ""
        assert ob.object == ""
        assert ob.condition is None
        assert ob.exception is None

    def test_full_construction(self) -> None:
        ob = Obligation(
            subject="driver",
            action="possess",
            object="valid licence",
            condition="driving motor vehicle",
            exception="learner permit holders",
        )
        assert ob.subject == "driver"
        assert ob.action == "possess"
        assert ob.object == "valid licence"
        assert ob.condition == "driving motor vehicle"
        assert ob.exception == "learner permit holders"

    def test_condition_only(self) -> None:
        ob = Obligation(
            subject="person", action="notify", object="authority", condition="data breach",
        )
        assert ob.condition == "data breach"
        assert ob.exception is None

    def test_repr(self) -> None:
        ob = Obligation(subject="x", action="y", object="z")
        assert "subject=" in repr(ob)
        assert "action=" in repr(ob)
        assert "object=" in repr(ob)

    def test_equality_by_value(self) -> None:
        a = Obligation(subject="s", action="a", object="o")
        b = Obligation(subject="s", action="a", object="o")
        assert a == b

    def test_inequality(self) -> None:
        a = Obligation(subject="s", action="a", object="o")
        b = Obligation(subject="s", action="a", object="other")
        assert a != b


class TestClauseMeaning:
    def test_default_construction(self) -> None:
        cm = ClauseMeaning()
        assert cm.clause_id == ""
        assert cm.obligations == []

    def test_with_obligations(self) -> None:
        obs = [
            Obligation(subject="controller", action="obtain", object="consent"),
            Obligation(subject="controller", action="notify", object="board"),
        ]
        cm = ClauseMeaning(clause_id="3.1", obligations=obs)
        assert cm.clause_id == "3.1"
        assert len(cm.obligations) == 2

    def test_empty_obligations(self) -> None:
        cm = ClauseMeaning(clause_id="4.2", obligations=[])
        assert cm.clause_id == "4.2"
        assert cm.obligations == []
