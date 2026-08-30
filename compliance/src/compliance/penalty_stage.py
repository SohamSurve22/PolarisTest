"""Penalty eligibility after status. Missing language is not a finding of liability."""

from __future__ import annotations

from graph_builder.catalog_ir import CatalogPenalty

from compliance.models import ObligationFinding, PenaltyFinding

_DISCLAIMER = True
_NO_PENALTY = frozenset({"covered", "not_applicable"})


def penalty_rows(
  finding: ObligationFinding,
  links: list[CatalogPenalty],
) -> list[PenaltyFinding]:
  if finding.status in _NO_PENALTY:
    return []
  if finding.status == "violation":
    eligibility = "may_trigger"
    trigger = "Policy text conflicts with the duty; a breach may trigger the linked provision."
    reason = "Potential consequence if the conflicting practice were established. Not a determination of liability."
    confidence = 0.7
  elif finding.status == "conflict":
    eligibility = "potential_exposure"
    trigger = "Contradictory policy text."
    reason = "Contradictory policy text. Not a determination of liability."
    confidence = 0.5
  else:
    eligibility = "potential_exposure"
    trigger = "If a breach of this duty were established."
    reason = (
      "Potential maximum penalty if a breach of this duty were established. "
      "Missing or partial policy language is not a finding of legal violation."
    )
    confidence = 0.4 if finding.status == "undetermined" else 0.45

  rows: list[PenaltyFinding] = []
  for link in links:
    rows.append(
      PenaltyFinding(
        obligation_id=finding.obligation_id,
        title=link.title,
        amount_crore=link.amount_crore,
        imprisonment_years=link.imprisonment_years,
        summary=link.summary,
        act=link.act,
        eligibility=eligibility,
        trigger_condition=trigger,
        confidence=confidence,
        reason=reason,
        not_a_determination_of_liability=_DISCLAIMER,
      )
    )
  return rows
