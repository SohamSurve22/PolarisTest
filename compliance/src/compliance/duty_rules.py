"""Sidecar law-version and per-duty reasoning rules."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_DATA = Path(__file__).parent / "data"

Severity = Literal["critical", "high", "medium", "low"]
LawStatus = Literal["ACTIVE", "PARTIALLY_COMMENCED", "REPEALED", "SUPERSEDED", "HISTORICAL"]


class RequirementElementSpec(BaseModel):
  id: str
  label: str
  keywords: list[str] = Field(default_factory=list)


class DutyRule(BaseModel):
  roles_any: list[str] = Field(default_factory=list)
  document_types: list[str] = Field(default_factory=lambda: ["privacy_policy"])
  requirement_elements: list[RequirementElementSpec] = Field(default_factory=list)
  severity: Severity = "medium"
  exact_terms: list[str] = Field(default_factory=list)
  contradiction_cues: list[str] = Field(default_factory=list)
  generic_phrases: list[str] = Field(default_factory=list)


class LawVersionMeta(BaseModel):
  status: LawStatus
  commencement_status: str = ""
  still_scored: bool = True
  effective_from: str | None = None
  effective_until: str | None = None
  supersedes: list[str] = Field(default_factory=list)
  superseded_by: str | None = None
  reason: str = ""


def _data_path(name: str) -> Path:
  return _DATA / name


@lru_cache(maxsize=1)
def load_law_versions(path: Path | None = None) -> dict[str, LawVersionMeta]:
  payload = (path or _data_path("law_versions.json")).read_text(encoding="utf-8")
  raw = json.loads(payload)
  return {act: LawVersionMeta.model_validate(row) for act, row in raw.items()}


@lru_cache(maxsize=1)
def load_duty_rules(path: Path | None = None) -> dict[str, DutyRule]:
  payload = (path or _data_path("duty_rules.json")).read_text(encoding="utf-8")
  raw = json.loads(payload)
  return {oid: DutyRule.model_validate(row) for oid, row in raw.items()}


def resolve_duty_rule(
  obligation_id: str,
  *,
  rules: dict[str, DutyRule] | None = None,
  catalog_roles: tuple[str, ...] = (),
) -> DutyRule:
  table = rules if rules is not None else load_duty_rules()
  if obligation_id in table:
    return table[obligation_id]
  roles = list(catalog_roles) if catalog_roles else ["ENTITY_DATA_FIDUCIARY"]
  return DutyRule(roles_any=roles, document_types=["privacy_policy"])
