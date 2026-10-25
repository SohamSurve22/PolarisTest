"""Path B: fake Jev client, statuses unchanged, undetermined, no 503."""

from __future__ import annotations

from compliance.jev import JevClient, JevError
from compliance.models import ObligationStatus, ObligationFinding
import pytest

from compliance.service import AnalyzeError, analyze_document
from compliance.jev_wire import jev
from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from pathlib import Path

from compliance.duty_rules import DutyRule

FIXTURE = Path(__file__).parent / "fixtures" / "analyze_law.json"


def _clause(text: str, clause_id: str = "S002_C001") -> Clause:
    return Clause(
        clause_id=clause_id,
        section_id="S002",
        section_title="Security",
        document_id="DOC_x",
        document_type=DocumentFormat.TXT,
        clause_text=text,
        span=Span(start=0, end=len(text)),
    )


def _document(*clauses: Clause) -> EntityDocument:
    entity_clauses = []
    for clause in clauses:
        classified = ClassifiedClause(
            clause=clause,
            role=StructuralRole.STATEMENT,
            confidence=1.0,
            classification_reason=[],
        )
        entity_clauses.append(
            EntityClause(
                contextual_clause=ContextualClause(classified_clause=classified),
                entities=[],
            )
        )
    return EntityDocument(
        metadata=DocumentMetadata(
            document_id="DOC_x",
            filename="policy.txt",
            format=DocumentFormat.TXT,
        ),
        entity_clauses=entity_clauses,
    )


class _FakeJevClient:
    """Deterministic Jev; any string outside the ObligationStatus set becomes
    "undetermined"."""

    def __init__(self, status: str = "covered", clause_ids: list[str] | None = None):
        self.status = status
        self.clause_ids = clause_ids or []
        self.calls: list[dict[str, object]] = []

    def classify_applicable_duty(self, *, obligation_id, act, title, summary,
                                 requirement_elements, policy_clauses, fallback_=False):
        self.calls.append(
            {
                "obligation_id": obligation_id,
                "act": act,
                "title": title,
                "summary": summary,
                "requirement_elements": requirement_elements,
                "policy_clauses": policy_clauses,
            }
        )
        if self.status not in ObligationStatus.__args__:
            return {"status": "undetermined", "clause_ids": [], "reason": "bad", "confidence": 0.0}
        return {
            "status": self.status,
            "clause_ids": list(self.clause_ids),
            "reason": f"Jev says {self.status}",
            "confidence": 0.8,
        }


def _rule() -> DutyRule:
    return DutyRule(
        roles_any=["ENTITY_DATA_FIDUCIARY"],
        document_types=["privacy_policy"],
        requirement_elements=[
            DutyRule.model_fields["requirement_elements"].default_factory[0](
                id="encryption", label="Encryption", keywords=["encrypt"]
            )
        ],
        contradiction_cues=["we do not encrypt"],
        generic_phrases=["applicable law"],
    )


def test_jev_status_is_authoritative() -> None:
    client = _FakeJevClient(status="covered", clause_ids=["S002_C001"])
    result = analyze_document(
        _document(_clause("We encrypt.")), [FIXTURE], search=lambda _: [], jev_client=client
    )

    row = next(r for r in result.obligations if r.obligation_id == "TINY_CONSENT")
    assert row.status == "covered"
    assert row.jev_status == "covered"
    assert row.jev_clause_ids == ["S002_C001"]
    assert row.jev_confidence == 0.8


def test_jev_out_of_set_is_undetermined() -> None:
    client = _FakeJevClient(status="bogus")
    result = analyze_document(
        _document(_clause("We encrypt.")), [FIXTURE], search=lambda _: [], jev_client=client
    )

    row = next(r for r in result.obligations if r.obligation_id == "TINY_CONSENT")
    assert row.status == "undetermined"
    assert row.jev_status == "undetermined"
    assert row.jev_reason == "bad"


def test_qwen_disagreement_does_not_change_jev_strip() -> None:
    jev_client = _FakeJevClient(status="covered")

    class _FakeQwen:
        def classify_applicable_duty(self, **_kwargs):
            return {"status": "violation", "reason": "Qwen disagrees", "confidence": 0.9}

    result = analyze_document(
        _document(_clause("We encrypt.")),
        [FIXTURE],
        search=lambda _: [],
        jev_client=jev_client,
        qwen_client=_FakeQwen(),
    )

    row = next(r for r in result.obligations if r.obligation_id == "TINY_CONSENT")
    assert row.status == "covered"
    assert row.qwen_status == "violation"


def test_analyze_does_not_call_qdrant_search() -> None:
    def should_not_run(_query: str):
        raise AssertionError("legacy Qdrant scorer was called")

    result = analyze_document(
        _document(_clause("We encrypt.")),
        [FIXTURE],
        search=should_not_run,
        jev_client=_FakeJevClient(status="missing"),
    )
    row = next(r for r in result.obligations if r.obligation_id == "TINY_CONSENT")
    assert row.status == "missing"


def test_jev_error_is_analyze_error() -> None:
    class _BrokenJev:
        def classify_applicable_duty(self, **_kwargs):
            raise JevError("Jev unavailable")

    with pytest.raises(AnalyzeError, match="Jev"):
        analyze_document(
            _document(_clause("We encrypt.")),
            [FIXTURE],
            search=lambda _: [],
            jev_client=_BrokenJev(),
        )


def test_decisions_preview_body_is_explicitly_supplied(monkeypatch) -> None:
    import compliance.jev as jev_module

    monkeypatch.setattr(jev_module, "DECISIONS_PREVIEW_BODY", '{"input": "{{title}}"}')
    assert JevClient._decisions_body({"title": "Consent"}) == {"input": "Consent"}


def test_decisions_preview_body_rejects_invalid_json(monkeypatch) -> None:
    import compliance.jev as jev_module

    monkeypatch.setattr(jev_module, "DECISIONS_PREVIEW_BODY", "not-json")
    with pytest.raises(JevError, match="valid JSON"):
        JevClient._decisions_body({"title": "Consent"})


def test_decisions_preview_parse_rejects_malformed_response() -> None:
    with pytest.raises(JevError, match="invalid JSON"):
        JevClient._decisions_parse("not-json")
    with pytest.raises(JevError, match="invalid output JSON"):
        JevClient._decisions_parse('{"output": "not-json"}')


def test_decisions_preview_parse_requires_object_output() -> None:
    with pytest.raises(JevError, match="non-object"):
        JevClient._decisions_parse('{"output": "[]"}')


def test_chat_fallback_uses_luna_and_strict_json(monkeypatch) -> None:
    import sys
    import types

    captured = {}

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(
                    content='{"status":"covered","clause_ids":[],"reason":"ok","confidence":0.9}'
                ))]
            )

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = lambda **_kwargs: types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=_Completions())
    )
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setattr("compliance.jev.CHAT_MODEL", "gpt-6-luna")

    client = JevClient.__new__(JevClient)
    result = client._chat_client()({"obligation_id": "D1"})

    assert result["status"] == "covered"
    assert captured["model"] == "gpt-6-luna"
    assert captured["response_format"] == {"type": "json_object"}



def test_jev_not_called_for_not_applicable() -> None:
    client = _FakeJevClient(status="violation")
    original = jev._client
    try:
        jev._client = client
        from compliance.applicability import default_entity_profile
        from compliance.service import analyze_document
        result = analyze_document(
            _document(_clause("We encrypt.")),
            [FIXTURE],
            search=lambda _: [],
            profile=default_entity_profile(roles=()),
        )
    finally:
        jev._client = original

    assert all(row.jev_status == "" for row in result.obligations)
