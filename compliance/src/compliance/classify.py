"""Deterministic status from evidence + duty rules. LLM does not classify."""

from __future__ import annotations

from compliance.duty_rules import DutyRule
from compliance.matching import EvidenceBundle
from compliance.models import ObligationStatus, RequirementElementFinding

ELEMENT_COVERED_RATIO = 0.60


def classify_duty(
  *,
  applicable: bool,
  evidence: EvidenceBundle,
  rule: DutyRule,
) -> tuple[ObligationStatus, float, list[RequirementElementFinding]]:
  elements = [
    RequirementElementFinding(
      id=spec.id,
      label=spec.label,
      satisfied=spec.id in evidence.element_hits,
    )
    for spec in rule.requirement_elements
  ]
  if not applicable:
    return "not_applicable", 1.0, elements

  blob = " ".join(evidence.expanded_texts).lower()
  if _contradiction(blob, rule.contradiction_cues):
    positive = any(item.satisfied for item in elements) or evidence.title_overlap
    if positive and _has_positive_clause(evidence, rule):
      return "conflict", 0.7, elements
    return "violation", 0.9, elements

  if evidence.quality == "NO_RELIABLE_MATCH" and not evidence.element_hits:
    return "missing", 0.8, elements

  if evidence.quality == "LOW" or (evidence.generic_only and not evidence.exact_term_hit):
    return "undetermined", 0.4, elements

  satisfied = sum(1 for item in elements if item.satisfied)
  if elements:
    ratio = satisfied / len(elements)
    if ratio >= ELEMENT_COVERED_RATIO and evidence.quality == "HIGH":
      return "covered", 0.9, elements
    if satisfied or evidence.quality in {"HIGH", "MEDIUM"}:
      return "partial", 0.65, elements
    return "missing", 0.8, elements

  if evidence.quality == "HIGH" and evidence.title_overlap:
    return "covered", 0.9, elements
  if evidence.quality in {"HIGH", "MEDIUM"}:
    return "partial", 0.65, elements
  return "missing", 0.8, elements


def _contradiction(blob: str, cues: list[str]) -> bool:
  return any(cue.lower() in blob for cue in cues if cue)


def _has_positive_clause(evidence: EvidenceBundle, rule: DutyRule) -> bool:
  if len(evidence.expanded_texts) < 2:
    return False
  cues = [cue.lower() for cue in rule.contradiction_cues if cue]
  keywords = [kw.lower() for spec in rule.requirement_elements for keyword in spec.keywords if keyword]
  has_cue = False
  has_pos = False
  for text in evidence.expanded_texts:
    lowered = text.lower()
    if any(cue in lowered for cue in cues):
      has_cue = True
    if any(keyword in lowered for keyword in keywords):
      has_pos = True
  return has_cue and has_pos
