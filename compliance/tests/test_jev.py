"""Path B: fake Jev client, statuses unchanged, undetermined, no 503."""

from __future__ import annotations

from compliance.jev import JevClient, JevError
from compliance.models import ObligationStatus, ObligationFinding
from compliance.service import analyze_document
from compliance.jev_wire import jev
from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from pathlib import Path

from compliance.duty_rules import DutyRule


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


def test_jev_status_is_sidecar_and_status_unchanged() -> None:
    client = _FakeJevClient(status="covered", clause_ids=["S002_C001"])
    original = jev._client
    try:
        jev._client = client
        result = analyze_document(_document(_clause("We encrypt.")), [], search=lambda _: [])
    finally:
        jev._client = original

    row = next(r for r in result.obligations if r.obligation_id == "DPDP_SEC_8_SUB_5")
    assert row.status == "covered"
    assert row.jev_status == "covered"
    assert row.jev_clause_ids == ["S002_C001"]
    assert row.jev_confidence == 0.8


def test_jev_out_of_set_is_undetermined() -> None:
    client = _FakeJevClient(status="bogus")
    original = jev._client
    try:
        jev._client = client
        result = analyze_document(_document(_clause("We encrypt.")), [], search=lambda _: [])
    finally:
        jev._client = original

    row = next(r for r in result.obligations if r.obligation_id == "DPDP_SEC_8_SUB_5")
    assert row.status == "covered"
    assert row.jev_status == "undetermined"
    assert row.jev_reason == "bad"


def test_jev_error_does_not_503() -> None:
    original = jev._client
    try:
        jev._client = None  # type: ignore[assignment]
        result = analyze_document(_document(_clause("We encrypt.")), [], search=lambda _: [])
    finally:
        jev._client = original

    assert result.obligations, "Path A must stay usable when Jev fails"
    row = result.obligations[0]
    assert row.jev_status == ""


def test_jev_not_called_for_not_applicable() -> None:
    client = _FakeJevClient(status="violation")
    original = jev._client
    try:
        jev._client = client
        from compliance.applicability import default_entity_profile
        from compliance.service import analyze_document
        result = analyze_document(
            _document(_clause("We encrypt.")),
            [],
            search=lambda _: [],
            profile=default_entity_profile(roles=()),
        )
    finally:
        jev._client = original

    row = next(r for r in result.obligations if r.obligation_id == "DPDP_SEC_8_SUB_5")
    assert row.status == "not_applicable"
    assert row.jev_status == ""
