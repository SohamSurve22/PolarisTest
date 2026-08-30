"""India/DPDP analysis: GraphIR duties scored against policy clauses via Qdrant."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.semantic import StructuralRole
from vectorization.models import SearchHit
from vectorization.sources import clause_from_entity

from compliance.applicability import EntityProfile, apply_duty, default_entity_profile
from compliance.classify import classify_duty
from compliance.duty_rules import load_duty_rules, load_law_versions, resolve_duty_rule
from compliance.explain import explain_finding
from compliance.graph_scope import ir_from_paths, obligation_nodes, penalties_for
from compliance.matching import PARTIAL_SCORE, collect_credits, gather_evidence
from compliance.models import (
  AnalysisResult,
  GapFinding,
  ObligationFinding,
  PenaltyFinding,
)
from compliance.penalty_stage import penalty_rows
from compliance.report import _weighted_pct

SUPPORTED_JURISDICTIONS = frozenset({"IN", "INDIA", "IN-DPDP"})
_GAP_STATUSES = frozenset({"missing", "partial", "undetermined", "conflict", "violation"})

SearchFn = Callable[[str], list[SearchHit]]

SearchFn = Callable[[str], list[SearchHit]]


class AnalyzeError(Exception):
  """Search backend (Qdrant / Ollama) is unavailable."""


def default_search(query: str) -> list[SearchHit]:
  from vectorization.pipeline import search_text

  # Floor at PARTIAL_SCORE so 0.30–0.54 hits are not dropped by the 0.55 search default.
  return search_text(query, source_type="kg_obligation", min_score=PARTIAL_SCORE)


def analyze_document(
  document: EntityDocument,
  law_paths: list[Path],
  *,
  jurisdiction: str = "IN",
  search: SearchFn | None = None,
  profile: EntityProfile | None = None,
  analysis_date: date | None = None,
  roles: Iterable[str] | None = None,
) -> AnalysisResult:
  code = (jurisdiction or "IN").strip().upper()
  if code not in SUPPORTED_JURISDICTIONS:
    msg = f"Unsupported jurisdiction: {jurisdiction}"
    raise ValueError(msg)

  entity_profile = profile or default_entity_profile(
    jurisdiction=code,
    analysis_date=analysis_date,
    roles=roles,
  )
  ir = ir_from_paths(law_paths)
  duties = obligation_nodes(ir)
  rules = load_duty_rules()
  versions = load_law_versions()
  decisions: dict[str, tuple[object, str, str, object]] = {}
  scored: list[object] = []
  for node in duties:
    props = node.properties or {}
    act = str(props.get("act") or "")
    raw_entities = props.get("entity_ids") or ()
    catalog_roles = tuple(str(item) for item in raw_entities)
    rule = resolve_duty_rule(node.id, rules=rules, catalog_roles=catalog_roles)
    version = versions.get(act)
    decision = apply_duty(rule, version, entity_profile)
    law_status = version.status if version is not None else ""
    decisions[node.id] = (decision, law_status, act, rule)
    if decision.applicable:
      scored.append(node)

  search_fn = search or default_search
  clauses = _policy_clauses(document)
  scored_ids = {node.id for node in scored}

  try:
    credited = collect_credits(clauses, search_fn, scored_ids)
  except ValueError:
    raise
  except Exception as exc:
    raise AnalyzeError(str(exc)) from exc

  obligations: list[ObligationFinding] = []
  for node in duties:
    decision, law_status, act, rule = decisions[node.id]
    props = node.properties or {}
    title = str(props.get("title") or node.id)
    summary = str(props.get("summary") or "")
    if not decision.applicable:
      row = ObligationFinding(
        obligation_id=node.id,
        title=title,
        summary=summary,
        act=act,
        status="not_applicable",
        applicability_reason=decision.reason,
        law_status=law_status,
        confidence=1.0,
        reason=decision.reason,
        severity=rule.severity,
      )
      row.reason = explain_finding(row)
      obligations.append(row)
      continue
    evidence = gather_evidence(node.id, title, rule, clauses, credited.get(node.id, []))
    status, confidence, elements = classify_duty(
      applicable=True,
      evidence=evidence,
      rule=rule,
    )
    row = ObligationFinding(
      obligation_id=node.id,
      title=title,
      summary=summary,
      act=act,
      status=status,
      score=evidence.score,
      matched_clause_ids=[item.clause_id for item in evidence.matched_clauses],
      matched_clauses=evidence.matched_clauses,
      applicability_reason=decision.reason,
      law_status=law_status,
      confidence=confidence,
      evidence_quality=evidence.quality,
      elements=elements,
      severity=rule.severity,
    )
    row.reason = explain_finding(row, evidence)
    obligations.append(row)

  gaps = [
    GapFinding(
      obligation_id=row.obligation_id,
      title=row.title,
      status=row.status,
      act=row.act,
      summary=row.summary,
    )
    for row in obligations
    if row.status in _GAP_STATUSES
  ]

  penalties: list[PenaltyFinding] = []
  seen: set[tuple[str, str]] = set()
  for row in obligations:
    for item in penalty_rows(row, penalties_for(ir, row.obligation_id)):
      key = (item.title, row.obligation_id, item.eligibility)
      if key in seen:
        continue
      seen.add(key)
      penalties.append(item)

  laws = sorted({
    row.act for row in obligations if row.act and row.status != "not_applicable"
  })
  return AnalysisResult(
    document_id=document.metadata.document_id,
    source_filename=str(document.metadata.filename or ""),
    jurisdiction=code,
    applicable_laws=laws,
    obligations=obligations,
    gaps=gaps,
    penalties=penalties,
    weighted_pct=_weighted_pct([row for row in obligations if row.status != "not_applicable"]),
  )


def _policy_clauses(document: EntityDocument) -> list[Clause]:
  clauses: list[Clause] = []
  for item in document.entity_clauses:
    clause = clause_from_entity(item)
    if clause is None:
      continue
    classified = getattr(getattr(item, "contextual_clause", None), "classified_clause", None)
    role = getattr(classified, "role", None)
    if role == StructuralRole.HEADING:
      continue
    if not (clause.clause_text or "").strip():
      continue
    clauses.append(clause)
  return clauses
