from document_pipeline.models.clause import Clause
from document_pipeline.models.metadata import DocumentFormat, Span

from compliance.classify import classify_duty
from compliance.duty_rules import DutyRule, RequirementElementSpec, load_duty_rules
from compliance.matching import EvidenceBundle, gather_evidence
from compliance.models import MatchedClause


def _rule() -> DutyRule:
  return DutyRule(
    roles_any=["ENTITY_DATA_FIDUCIARY"],
    document_types=["privacy_policy"],
    requirement_elements=[
      RequirementElementSpec(id="encryption", label="Encryption", keywords=["encrypt"]),
      RequirementElementSpec(id="logging", label="Logging", keywords=["log"]),
    ],
    contradiction_cues=["we do not encrypt"],
    generic_phrases=["applicable law"],
  )


def _clause(text: str, clause_id: str = "c1") -> Clause:
  return Clause(
    clause_id=clause_id,
    section_id="S001",
    section_title="Security",
    document_id="DOC_x",
    document_type=DocumentFormat.TXT,
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )


def test_not_applicable_short_circuits() -> None:
  status, confidence, _elements = classify_duty(
    applicable=False,
    evidence=EvidenceBundle(),
    rule=_rule(),
  )
  assert status == "not_applicable"
  assert confidence == 1.0


def test_contradiction_is_violation() -> None:
  evidence = EvidenceBundle(
    score=0.9,
    quality="HIGH",
    expanded_texts=["We do not encrypt personal data."],
    matched_clauses=[MatchedClause(clause_id="c1", text="We do not encrypt personal data.")],
    contradiction_clauses=[_clause("We do not encrypt personal data.")],
  )
  status, _confidence, elements = classify_duty(applicable=True, evidence=evidence, rule=_rule())
  assert status == "violation"
  assert all(item.result != "supported" or item.satisfied for item in elements)


def test_cue_never_returns_covered() -> None:
  evidence = EvidenceBundle(
    score=0.9,
    quality="HIGH",
    element_hits=["encryption", "logging"],
    title_overlap=True,
    expanded_texts=["We encrypt and log access."],
    contradiction_clauses=[_clause("We do not encrypt personal data.")],
  )
  status, _confidence, _elements = classify_duty(applicable=True, evidence=evidence, rule=_rule())
  assert status != "covered"
  assert status in {"violation", "conflict"}


def test_positive_credited_and_cue_is_conflict() -> None:
  positive = MatchedClause(clause_id="c_pos", text="We encrypt and log access.")
  evidence = EvidenceBundle(
    score=0.9,
    quality="HIGH",
    element_hits=["encryption", "logging"],
    title_overlap=True,
    matched_clauses=[positive],
    contradiction_clauses=[_clause("We do not encrypt personal data.", "c_neg")],
    has_credited_support=True,
  )
  status, _confidence, _elements = classify_duty(applicable=True, evidence=evidence, rule=_rule())
  assert status == "conflict"


def test_no_reliable_match_is_missing() -> None:
  status, confidence, _elements = classify_duty(
    applicable=True,
    evidence=EvidenceBundle(quality="NO_RELIABLE_MATCH"),
    rule=_rule(),
  )
  assert status == "missing"
  assert confidence == 0.8


def test_generic_only_is_undetermined() -> None:
  evidence = EvidenceBundle(
    score=0.5,
    quality="MEDIUM",
    generic_only=True,
    expanded_texts=["We comply with all applicable laws."],
  )
  status, _confidence, _elements = classify_duty(applicable=True, evidence=evidence, rule=_rule())
  assert status == "undetermined"


def test_majority_elements_and_high_is_covered() -> None:
  evidence = EvidenceBundle(
    score=0.8,
    quality="HIGH",
    element_hits=["encryption", "logging"],
    title_overlap=True,
    expanded_texts=["We encrypt and log access."],
  )
  status, _confidence, elements = classify_duty(applicable=True, evidence=evidence, rule=_rule())
  assert status == "covered"
  assert all(item.satisfied for item in elements)
  assert all(item.result == "supported" for item in elements)


def test_some_elements_is_partial() -> None:
  evidence = EvidenceBundle(
    score=0.8,
    quality="HIGH",
    element_hits=["encryption"],
    title_overlap=True,
    expanded_texts=["We encrypt data."],
  )
  status, _confidence, elements = classify_duty(applicable=True, evidence=evidence, rule=_rule())
  assert status == "partial"
  assert sum(1 for item in elements if item.satisfied) == 1
  assert {item.id: item.result for item in elements}["logging"] == "absent"


def test_quickbazaar_fixture_marks_listed_duties_violation() -> None:
  rules = load_duty_rules()
  clauses = [
    _clause("Once provided, consent cannot be withdrawn.", "c_wd"),
    _clause(
      "QuickBazaar may deny a request to delete, erase, anonymise, correct, access, retrieve "
      "or otherwise manage Personal Data under all circumstances. Personal Data may be "
      "retained indefinitely, permanently or for unspecified future purposes.",
      "c_del",
    ),
    _clause(
      "QuickBazaar does not provide a dedicated privacy grievance officer, Data Protection "
      "Officer, complaint portal, telephone line, postal channel, email address or other "
      "grievance redressal mechanism.",
      "c_gr",
    ),
    _clause(
      "QuickBazaar may collect, use, disclose, profile, retain and otherwise process Personal "
      "Data relating to children without obtaining verifiable consent from a parent or lawful "
      "guardian and without applying any additional safeguards.",
      "c_ch",
    ),
    _clause(
      "Notwithstanding anything else in this Privacy Policy, users waive all privacy-related "
      "rights, claims, requests and remedies simply by accessing or using the Services.",
      "c_wv",
    ),
  ]
  expected = {
    "DPDP_SEC_6_SUB_5": "Withdrawal",
    "DPDP_SEC_8_SUB_7": "Erasure",
    "DPDP_SEC_8_SUB_10": "Grievance",
    "DPDP_SEC_9_SUB_1": "Children",
  }
  for oid, title in expected.items():
    evidence = gather_evidence(oid, title, rules[oid], clauses, [])
    status, _confidence, elements = classify_duty(applicable=True, evidence=evidence, rule=rules[oid])
    assert status == "violation", (oid, status)
    assert any(item.result == "contradicted" for item in elements) or evidence.contradiction_clauses
