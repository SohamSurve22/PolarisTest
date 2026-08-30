"""Deterministic law/duty applicability for an analysis profile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from compliance.duty_rules import DutyRule, LawVersionMeta

_IN = frozenset({"IN", "INDIA", "IN-DPDP"})
DEFAULT_ROLES: frozenset[str] = frozenset({"ENTITY_DATA_FIDUCIARY", "ENTITY_BODY_CORPORATE"})


@dataclass(frozen=True)
class EntityProfile:
  document_type: str
  roles: frozenset[str]
  analysis_date: date
  jurisdiction: str


@dataclass(frozen=True)
class ApplicabilityDecision:
  applicable: bool
  reason: str


def default_entity_profile(
  *,
  jurisdiction: str = "IN",
  document_type: str = "privacy_policy",
  roles: Iterable[str] | None = None,
  analysis_date: date | None = None,
) -> EntityProfile:
  return EntityProfile(
    document_type=document_type or "privacy_policy",
    roles=frozenset(roles) if roles is not None else DEFAULT_ROLES,
    analysis_date=analysis_date or date.today(),
    jurisdiction=(jurisdiction or "IN").strip().upper(),
  )


def apply_duty(
  rule: DutyRule,
  version: LawVersionMeta | None,
  profile: EntityProfile,
) -> ApplicabilityDecision:
  code = (profile.jurisdiction or "").strip().upper()
  if code not in _IN:
    return ApplicabilityDecision(False, f"jurisdiction {profile.jurisdiction} is not in scope")

  if version is not None:
    start = _parse_date(version.effective_from)
    end = _parse_date(version.effective_until)
    if start is not None and profile.analysis_date < start:
      return ApplicabilityDecision(
        False,
        f"provision is not yet effective as of {profile.analysis_date.isoformat()}",
      )
    if end is not None and profile.analysis_date > end:
      return ApplicabilityDecision(
        False,
        f"provision was not in force on {profile.analysis_date.isoformat()}",
      )
    if version.status == "REPEALED" and not version.still_scored:
      return ApplicabilityDecision(False, "provision is repealed and is not still scored")

  if rule.roles_any and profile.roles.isdisjoint(set(rule.roles_any)):
    return ApplicabilityDecision(
      False,
      f"profile roles {sorted(profile.roles)} do not match required roles {rule.roles_any}",
    )
  if rule.document_types and profile.document_type not in rule.document_types:
    return ApplicabilityDecision(
      False,
      f"document type {profile.document_type} is not in {sorted(rule.document_types)}",
    )

  status = version.status if version is not None else ""
  reason = "applicable"
  if status:
    reason = f"applicable under {status}"
    if version is not None and version.reason:
      reason = f"{reason}; {version.reason}"
  return ApplicabilityDecision(True, reason)


def _parse_date(value: str | None) -> date | None:
  if not value:
    return None
  try:
    return datetime.strptime(value, "%Y-%m-%d").date()
  except ValueError:
    return None
