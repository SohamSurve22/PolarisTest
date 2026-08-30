from compliance.citations import closest_citation
from compliance.models import MatchedClause, ObligationFinding


def test_closest_citation_uses_counter_evidence_for_violation() -> None:
  row = ObligationFinding(
    obligation_id="SPDI_RULE_6_SUB_1",
    title="Prior consent",
    status="violation",
    evidence_quality="HIGH",
    matched_clauses=[
      MatchedClause(
        clause_id="S014_C001",
        section_title="Accuracy and User Responsibilities",
        text="You are responsible for ensuring third-party info is accurate.",
      )
    ],
    counter_evidence=[
      MatchedClause(
        clause_id="S006_C001",
        section_title="Sharing and Disclosure of Personal Data",
        text="We may sell, rent, license, exchange, monetise Personal Data.",
      )
    ],
  )
  cited = closest_citation(row)
  assert "sell" in cited.lower()
  assert "Sharing" in cited
  assert "Accuracy and User Responsibilities" not in cited


def test_closest_citation_uses_counter_evidence_for_conflict() -> None:
  row = ObligationFinding(
    obligation_id="DPDP_SEC_9_SUB_3",
    title="No tracking children",
    status="conflict",
    evidence_quality="HIGH",
    matched_clauses=[
      MatchedClause(
        clause_id="S010_C001",
        section_title="Children",
        text="Parents are responsible for supervising children's use.",
      )
    ],
    counter_evidence=[
      MatchedClause(
        clause_id="S010_C001",
        section_title="Children",
        text="QuickBazaar may use children's Personal Data for advertising, targeted marketing, profiling.",
      )
    ],
  )
  cited = closest_citation(row)
  assert "advertising, targeted marketing, profiling" in cited
  assert "Parents are responsible" not in cited
