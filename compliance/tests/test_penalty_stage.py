from graph_builder.catalog_ir import CatalogPenalty

from compliance.models import ObligationFinding
from compliance.penalty_stage import penalty_rows


def _link() -> CatalogPenalty:
  return CatalogPenalty(
    penalty_id="P1",
    title="Fine",
    act="DPDP",
    obligation_ids=("D1",),
    amount_crore=250.0,
  )


def test_covered_and_not_applicable_have_no_penalty() -> None:
  covered = ObligationFinding(obligation_id="D1", title="Duty", status="covered")
  na = ObligationFinding(obligation_id="D1", title="Duty", status="not_applicable")
  assert penalty_rows(covered, [_link()]) == []
  assert penalty_rows(na, [_link()]) == []


def test_missing_is_potential_exposure_not_liability() -> None:
  missing = ObligationFinding(obligation_id="D1", title="Duty", status="missing")
  rows = penalty_rows(missing, [_link()])
  assert rows
  assert rows[0].eligibility == "potential_exposure"
  assert rows[0].not_a_determination_of_liability is True
  assert "not a finding of legal violation" in rows[0].reason.lower()


def test_violation_is_may_trigger() -> None:
  violation = ObligationFinding(obligation_id="D1", title="Duty", status="violation")
  rows = penalty_rows(violation, [_link()])
  assert rows[0].eligibility == "may_trigger"
  assert rows[0].not_a_determination_of_liability is True
