from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from vectorization.models import SearchHit

from compliance.duty_rules import load_duty_rules
from compliance.matching import clause_has_denial_polarity, find_contradictions, gather_evidence
from compliance.service import analyze_document

ROOT = Path(__file__).resolve().parents[2]


def _clause(text: str, *, clause_id: str = "S002_C001") -> Clause:
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


def _hit(obligation_id: str, score: float) -> SearchHit:
  return SearchHit(
    score=score,
    source_type="kg_obligation",
    payload={"obligation_id": obligation_id, "law_code": "DPDP"},
  )


def test_security_clause_credits_dpdp_and_is_not_missing() -> None:
  from policy_compare.service import default_law_paths

  text = (
    "BharatPay implements encryption, tokenisation, MFA, least-privilege access, "
    "logging, monitoring, backups and vendor due diligence."
  )

  def search(_query: str) -> list[SearchHit]:
    return [_hit("CERTIN_DIR_2", 0.80), _hit("DPDP_SEC_8_SUB_5", 0.78)]

  result = analyze_document(
    _document(_clause(text)),
    default_law_paths(ROOT),
    search=search,
  )
  by_id = {row.obligation_id: row for row in result.obligations}
  assert by_id["DPDP_SEC_8_SUB_5"].status != "missing"
  assert by_id["DPDP_SEC_8_SUB_5"].status in {"covered", "partial"}
  assert by_id["DPDP_SEC_8_SUB_5"].matched_clauses
  assert by_id["CERTIN_DIR_2"].matched_clauses


def test_unrelated_low_score_is_no_reliable_match() -> None:
  from policy_compare.service import default_law_paths

  def search(_query: str) -> list[SearchHit]:
    return [_hit("ITACT_SEC_43A", 0.32)]

  result = analyze_document(
    _document(_clause("Contact our grievance officer at complaints@example.com.")),
    default_law_paths(ROOT),
    search=search,
  )
  row = next(item for item in result.obligations if item.obligation_id == "ITACT_SEC_43A")
  assert row.evidence_quality == "NO_RELIABLE_MATCH"
  assert row.matched_clauses == []


def test_element_keywords_on_credited_positive_clause_are_medium() -> None:
  rule = load_duty_rules()["DPDP_SEC_8_SUB_5"]
  clause = _clause(
    "We use encryption, MFA, logging and vendor due diligence.",
    clause_id="S008_C001",
  )
  bundle = gather_evidence(
    "DPDP_SEC_8_SUB_5",
    "Security Safeguards",
    rule,
    [clause],
    [(clause, 0.78)],
  )
  assert bundle.element_hits
  assert bundle.quality in {"HIGH", "MEDIUM"}
  assert bundle.matched_clauses


def test_empty_credits_still_score_positive_keywords_for_stub_search() -> None:
  rule = load_duty_rules()["DPDP_SEC_8_SUB_5"]
  clause = _clause(
    "We use encryption, MFA, logging and vendor due diligence.",
    clause_id="S008_C001",
  )
  bundle = gather_evidence("DPDP_SEC_8_SUB_5", "Security Safeguards", rule, [clause], [])
  assert bundle.element_hits
  assert bundle.quality in {"HIGH", "MEDIUM"}


def test_denial_polarity_does_not_satisfy_withdrawal() -> None:
  rule = load_duty_rules()["DPDP_SEC_6_SUB_5"]
  clause = _clause("Once provided, consent cannot be withdrawn.", clause_id="S004_C001")
  bundle = gather_evidence("DPDP_SEC_6_SUB_5", "Withdrawal of consent", rule, [clause], [])
  assert "withdraw" not in bundle.element_hits
  assert clause_has_denial_polarity(clause.clause_text, rule)
  assert bundle.contradiction_clauses


def test_definition_clause_does_not_cover_security() -> None:
  from policy_compare.service import default_law_paths

  result = analyze_document(
    _document(_clause("Personal Data means any data about an identifiable individual.")),
    default_law_paths(ROOT),
    search=lambda _: [],
  )
  row = next(item for item in result.obligations if item.obligation_id == "DPDP_SEC_8_SUB_5")
  assert row.status != "covered"


def test_uncredited_keywords_are_ignored_when_credits_exist() -> None:
  rule = load_duty_rules()["DPDP_SEC_8_SUB_5"]
  definition = _clause("Personal Data means any data about an individual.", clause_id="S001_C001")
  security = _clause("We use encryption, MFA and logging.", clause_id="S008_C001")
  bundle = gather_evidence(
    "DPDP_SEC_8_SUB_5",
    "Security Safeguards",
    rule,
    [definition, security],
    [(definition, 0.80)],
  )
  assert "technical_measures" not in bundle.element_hits
  assert not bundle.matched_clauses or all("encrypt" not in item.text.lower() for item in bundle.matched_clauses)


def test_find_contradictions_scans_all_clauses() -> None:
  rule = load_duty_rules()["DPDP_SEC_6_SUB_5"]
  other = _clause("We publish this privacy policy on our website.", clause_id="S001_C001")
  denial = _clause("Once provided, consent cannot be withdrawn.", clause_id="S004_C001")
  hits = find_contradictions([other, denial], rule)
  assert any(item.clause_id == "S004_C001" for item in hits)
  assert all(item.clause_id != "S001_C001" for item in hits)


def test_neighbor_without_own_cue_is_not_a_contradiction() -> None:
  rule = load_duty_rules()["DPDP_SEC_8_SUB_10"]
  neighbor = _clause(
    "A request submitted through a third party may not be treated as a request to QuickBazaar.",
    clause_id="S013_C005",
  )
  neighbor.section_title = "Rights and Requests"
  denial = _clause(
    "QuickBazaar does not provide a dedicated privacy grievance officer.",
    clause_id="S014_C001",
  )
  denial.section_title = "Grievance Redressal"
  hits = find_contradictions([neighbor, denial], rule)
  assert [item.clause_id for item in hits] == ["S014_C001"]


def test_user_accuracy_clause_is_not_cited_for_fiduciary_disclosure() -> None:
  rule = load_duty_rules()["SPDI_RULE_6_SUB_1"]
  sharing = _clause(
    "Sharing and Disclosure of Personal Data. We may sell, rent, license, exchange, "
    "monetise Personal Data.",
    clause_id="S006_C001",
  )
  sharing.section_title = "Sharing and Disclosure of Personal Data"
  user = _clause(
    "Accuracy and User Responsibilities. You are responsible for ensuring that information "
    "supplied to QuickBazaar is accurate.",
    clause_id="S014_C001",
  )
  user.section_title = "Accuracy and User Responsibilities"
  bundle = gather_evidence(
    "SPDI_RULE_6_SUB_1",
    "Prior Consent Requirement for Disclosure",
    rule,
    [sharing, user],
    [(user, 0.90), (sharing, 0.70)],
  )
  cited = " ".join(item.text for item in bundle.matched_clauses)
  cited += " ".join(item.clause_text for item in bundle.contradiction_clauses)
  assert "Accuracy and User Responsibilities" not in cited
  assert "you are responsible" not in cited.lower()
  blob = " ".join(item.text for item in bundle.matched_clauses)
  blob += " ".join(item.clause_text for item in bundle.contradiction_clauses)
  assert "sell" in blob.lower() or "disclos" in blob.lower() or "sharing" in cited.lower()


def test_only_user_accuracy_clause_is_missing_for_disclosure() -> None:
  from compliance.classify import classify_duty

  rule = load_duty_rules()["SPDI_RULE_6_SUB_1"]
  user = _clause(
    "Accuracy and User Responsibilities. You are responsible for ensuring that any "
    "Personal Data you provide about a third party is accurate.",
    clause_id="S014_C001",
  )
  user.section_title = "Accuracy and User Responsibilities"
  bundle = gather_evidence(
    "SPDI_RULE_6_SUB_1",
    "Prior Consent Requirement for Disclosure",
    rule,
    [user],
    [(user, 0.90)],
  )
  status, _confidence, _elements = classify_duty(applicable=True, evidence=bundle, rule=rule)
  assert status == "missing"
  assert not bundle.matched_clauses


def test_children_citation_picks_advertising_sentence() -> None:
  rule = load_duty_rules()["DPDP_SEC_9_SUB_3"]
  clause = _clause(
    "Parents are responsible for supervising children's use of the Services. "
    "QuickBazaar may use children's Personal Data for advertising, targeted marketing, profiling.",
    clause_id="S010_C001",
  )
  clause.section_title = "Children"
  bundle = gather_evidence(
    "DPDP_SEC_9_SUB_3",
    "No Tracking or Targeted Advertising for Children",
    rule,
    [clause],
    [(clause, 0.80)],
  )
  texts = [item.text for item in bundle.matched_clauses]
  texts += [item.clause_text for item in bundle.contradiction_clauses]
  blob = " ".join(texts)
  assert "advertising, targeted marketing, profiling" in blob
  assert not any(
    item.text.startswith("Parents are responsible") for item in bundle.matched_clauses
  )


def test_children_split_clauses_cite_advertising_not_setup() -> None:
  from compliance.citations import closest_citation
  from compliance.classify import classify_duty
  from compliance.models import MatchedClause, ObligationFinding

  rule = load_duty_rules()["DPDP_SEC_9_SUB_3"]
  setup = _clause(
    "The Services may be used by children and other persons below the age of eighteen years.",
    clause_id="S009_C001",
  )
  setup.section_title = "Children's Personal Data"
  consent = _clause(
    "QuickBazaar may process Personal Data relating to children without obtaining "
    "verifiable consent from a parent.",
    clause_id="S009_C002",
  )
  consent.section_title = "Children's Personal Data"
  ads = _clause(
    "QuickBazaar may use children's Personal Data for advertising, targeted marketing, profiling.",
    clause_id="S009_C003",
  )
  ads.section_title = "Children's Personal Data"
  parents = _clause(
    "Parents are responsible for supervising children's use of the Services.",
    clause_id="S009_C004",
  )
  parents.section_title = "Children's Personal Data"
  clauses = [setup, consent, ads, parents]
  bundle = gather_evidence(
    "DPDP_SEC_9_SUB_3",
    "No Tracking or Targeted Advertising for Children",
    rule,
    clauses,
    [(parents, 0.80), (ads, 0.70)],
  )
  status, _confidence, _elements = classify_duty(applicable=True, evidence=bundle, rule=rule)
  first = bundle.contradiction_clauses[0].clause_text
  assert "advertising, targeted marketing, profiling" in first
  assert "Parents are responsible" not in first
  row = ObligationFinding(
    obligation_id="DPDP_SEC_9_SUB_3",
    title="No tracking",
    status=status,
    matched_clauses=bundle.matched_clauses,
    counter_evidence=[
      MatchedClause(
        clause_id=item.clause_id,
        section_title=item.section_title or "",
        text=item.clause_text,
      )
      for item in bundle.contradiction_clauses
    ],
  )
  cited = closest_citation(row)
  assert "advertising, targeted marketing, profiling" in cited
  assert "Parents are responsible" not in cited
