from compliance.classify import classify_duty
from compliance.duty_rules import DutyRule, RequirementElementSpec
from compliance.matching import EvidenceBundle
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
  )
  status, _confidence, _elements = classify_duty(applicable=True, evidence=evidence, rule=_rule())
  assert status == "violation"


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
