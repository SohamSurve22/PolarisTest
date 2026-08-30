from pathlib import Path

from compliance.catalog import load_catalog
from compliance.duty_rules import DutyRule, load_duty_rules, load_law_versions, resolve_duty_rule
from policy_compare.service import default_law_paths

ROOT = Path(__file__).resolve().parents[2]


def test_law_versions_lock_india_acts() -> None:
  versions = load_law_versions()
  dpdp = versions["DPDP"]
  assert dpdp.status == "ACTIVE"
  assert dpdp.commencement_status == "PARTIALLY_COMMENCED"
  assert dpdp.still_scored is True
  spdi = versions["SPDI_RULES_2011"]
  assert spdi.status == "SUPERSEDED"
  assert spdi.supersedes == []
  assert spdi.superseded_by == "DPDP"
  assert spdi.still_scored is True
  assert "continuing" in (spdi.reason or "").lower()
  itact = versions["IT_ACT_2000"]
  assert itact.status == "ACTIVE"
  assert itact.still_scored is True
  certin = versions["CERTIN_DIRECTIONS_2022"]
  assert certin.status == "ACTIVE"
  assert str(certin.effective_from) == "2022-06-28"


def test_duty_rules_cover_exactly_the_catalog() -> None:
  catalog = load_catalog(default_law_paths(ROOT))
  catalog_ids = {chunk.doc_id for chunk in catalog.obligations}
  rules = load_duty_rules()
  assert len(catalog_ids) == 63
  assert set(rules) == catalog_ids


def test_dpdp_security_has_encryption_access_logging_elements() -> None:
  rule = load_duty_rules()["DPDP_SEC_8_SUB_5"]
  assert "ENTITY_DATA_FIDUCIARY" in rule.roles_any
  assert "privacy_policy" in rule.document_types
  labels = " ".join(el.label.lower() + " " + " ".join(el.keywords) for el in rule.requirement_elements)
  assert "encrypt" in labels
  assert "access" in labels
  assert "log" in labels


def test_quickbazaar_contradiction_cues_cover_fail_policy_phrases() -> None:
  rules = load_duty_rules()
  assert "consent cannot be withdrawn" in rules["DPDP_SEC_6_SUB_5"].contradiction_cues
  assert "deny a request to delete" in rules["DPDP_SEC_8_SUB_7"].contradiction_cues
  assert any("dedicated privacy grievance" in cue for cue in rules["DPDP_SEC_8_SUB_10"].contradiction_cues)
  assert any("verifiable consent" in cue for cue in rules["DPDP_SEC_9_SUB_1"].contradiction_cues)
  assert any("waive all privacy-related rights" in cue for cue in rules["DPDP_SEC_6_SUB_5"].contradiction_cues)
  assert any("sell, rent, license" in cue for cue in rules["SPDI_RULE_6_SUB_1"].contradiction_cues)
  assert any("without regard to restrictions" in cue for cue in rules["DPDP_SEC_16_SUB_1"].contradiction_cues)
  assert any("no responsibility" in cue for cue in rules["ITACT_SEC_43A"].contradiction_cues)


def test_itact_sec_30_is_certifying_authority_only() -> None:
  rule = load_duty_rules()["ITACT_SEC_30"]
  assert rule.roles_any == ["ENTITY_CERTIFYING_AUTHORITY"]


def test_missing_rule_defaults_to_privacy_policy_and_catalog_roles() -> None:
  rule = resolve_duty_rule(
    "TINY_UNKNOWN",
    rules={},
    catalog_roles=("ENTITY_BODY_CORPORATE",),
  )
  assert isinstance(rule, DutyRule)
  assert rule.document_types == ["privacy_policy"]
  assert rule.roles_any == ["ENTITY_BODY_CORPORATE"]


def test_missing_rule_without_catalog_roles_defaults_to_data_fiduciary() -> None:
  rule = resolve_duty_rule("TINY_UNKNOWN", rules={}, catalog_roles=())
  assert rule.roles_any == ["ENTITY_DATA_FIDUCIARY"]
  assert rule.document_types == ["privacy_policy"]
  assert rule.bound_actor == "fiduciary"


def test_catalog_duties_default_bound_actor_fiduciary() -> None:
  rules = load_duty_rules()
  assert rules["SPDI_RULE_6_SUB_1"].bound_actor == "fiduciary"
  assert rules["DPDP_SEC_9_SUB_3"].bound_actor == "fiduciary"
