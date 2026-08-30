"""Deterministic status from evidence + duty rules. LLM does not classify."""

from __future__ import annotations

from compliance.duty_rules import DutyRule, RequirementElementSpec
from compliance.matching import EvidenceBundle, clause_has_denial_polarity, _norm
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
      result=_element_result(spec, evidence),
      satisfied=spec.id in evidence.element_hits,
    )
    for spec in rule.requirement_elements
  ]
  for item in elements:
    item.satisfied = item.result == "supported"
  if not applicable:
    return "not_applicable", 1.0, elements

  if _material_contradiction(evidence, rule):
    if evidence.has_credited_support and _has_positive_clause(evidence, rule):
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


def _element_result(spec: RequirementElementSpec, evidence: EvidenceBundle) -> str:
  if spec.id in evidence.element_hits:
    return "supported"
  blob = _norm(" ".join(item.clause_text for item in evidence.contradiction_clauses))
  if blob and any(_norm(keyword) in blob for keyword in spec.keywords if keyword):
    return "contradicted"
  return "absent"


def _material_contradiction(evidence: EvidenceBundle, rule: DutyRule) -> bool:
  if evidence.contradiction_clauses:
    return True
  blob = " ".join(evidence.expanded_texts).lower()
  return _contradiction(blob, rule.contradiction_cues)


def _contradiction(blob: str, cues: list[str]) -> bool:
  lowered = _norm(blob) if blob else ""
  return any(_norm(cue) in lowered for cue in cues if cue)


_WEAK_ALONE = frozenset({"contact", "officer", "email", "dpo"})


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
  lowered = text.lower()
  return [keyword for keyword in keywords if keyword in lowered]


def _has_keyword_support(text: str, keywords: list[str]) -> bool:
  hits = set(_keyword_hits(text, keywords))
  if not hits:
    return False
  if hits <= _WEAK_ALONE:
    return False
  return True


def _has_positive_clause(evidence: EvidenceBundle, rule: DutyRule) -> bool:
  cues = [cue.lower() for cue in rule.contradiction_cues if cue]
  keywords = [keyword.lower() for spec in rule.requirement_elements for keyword in spec.keywords if keyword]
  cue_ids = {item.clause_id for item in evidence.contradiction_clauses}
  if evidence.matched_clauses:
    for item in evidence.matched_clauses:
      if item.clause_id in cue_ids:
        continue
      lowered = item.text.lower()
      if any(cue in lowered for cue in cues):
        continue
      if clause_has_denial_polarity(item.text, rule):
        continue
      if _has_keyword_support(lowered, keywords):
        return True
    return False
  if len(evidence.expanded_texts) < 2:
    return False
  has_cue = False
  has_pos = False
  for text in evidence.expanded_texts:
    lowered = text.lower()
    if any(cue in lowered for cue in cues):
      has_cue = True
    elif _has_keyword_support(lowered, keywords) and not clause_has_denial_polarity(text, rule):
      has_pos = True
  return has_cue and has_pos
