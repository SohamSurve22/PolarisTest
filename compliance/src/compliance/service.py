"""India/DPDP analysis: GraphIR duties classified by OpenAI Jev."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from document_pipeline.models.clause import Clause
from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.semantic import StructuralRole
from vectorization.models import SearchHit
from vectorization.sources import clause_from_entity
from graph_builder.graph_ir import GraphIR

from compliance.applicability import EntityProfile, apply_duty, default_entity_profile
from compliance.jev import JevError
from compliance.jev_wire import AppliedDuty, jev
from compliance.qwen import QwenError
from compliance.qwen_wire import qwen
from compliance.duty_rules import load_duty_rules, load_law_versions, resolve_duty_rule
from compliance.explain import explain_finding
from compliance.graph_scope import ir_from_paths, obligation_nodes, penalties_for
from compliance.matching import EvidenceBundle, PARTIAL_SCORE, actor_filtered_text, best_sentence
from compliance.jurisdictions import default_registry
from compliance.models import (
  AnalysisResult,
  GapFinding,
  MatchedClause,
  ObligationFinding,
  ObligationStatus,
  PenaltyFinding,
)
from compliance.penalty_stage import penalty_rows
from compliance.report import _weighted_pct

if TYPE_CHECKING:
  from graph_builder.policy_graph_builder import PolicyGraphBuilder

_GAP_STATUSES = frozenset({"missing", "partial", "undetermined", "conflict", "violation"})
_ADVERSE_RANK = {
  "violation": 5,
  "conflict": 4,
  "missing": 3,
  "undetermined": 2,
  "partial": 1,
  "covered": 0,
}

SearchFn = Callable[[str], list[SearchHit]]


class AnalyzeError(Exception):
  """The authoritative Jev classifier is unavailable."""


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
  policy_builder: PolicyGraphBuilder | None = None,
  jev_client=None,
  qwen_client=None,
  graph_ir: GraphIR | None = None,
  duty_rules_path: Path | None = None,
  law_versions_path: Path | None = None,
) -> AnalysisResult:
  code = (jurisdiction or "IN").strip().upper()
  spec = default_registry().resolve(code)
  code = spec.code

  entity_profile = profile or default_entity_profile(
    jurisdiction=code,
    analysis_date=analysis_date,
    roles=roles,
  )
  if graph_ir is not None:
    ir = graph_ir
  elif duty_rules_path is not None or spec.duty_rules_path is not None:
    ir = ir_from_paths(law_paths, duty_rules_path=duty_rules_path or spec.duty_rules_path)
  else:
    ir = ir_from_paths(law_paths)
  duties = obligation_nodes(ir)
  rules = load_duty_rules(duty_rules_path or spec.duty_rules_path)
  versions = load_law_versions(law_versions_path or spec.law_versions_path)
  decisions: dict[str, tuple[object, str, str, object]] = {}
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
  clauses = _policy_clauses(document)
  clause_by_id = {clause.clause_id: clause for clause in clauses}
  authoritative_jev = jev if jev_client is None else jev_client
  comparison_qwen = qwen if qwen_client is None else qwen_client

  obligations: list[ObligationFinding] = []
  policy_clauses: list[dict[str, object]] = [
    {
      "clause_id": clause.clause_id,
      "section_title": clause.section_title,
      "text": clause.clause_text,
      "section_id": clause.section_id,
    }
    for clause in clauses
  ]
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
    try:
      jev_block = _jev_block(
        authoritative_jev, node, act, title, summary, rule, policy_clauses
      )
    except JevError as exc:
      raise AnalyzeError(str(exc)) from exc
    status = str(jev_block["status"])
    confidence = float(jev_block.get("confidence") or 0.0)
    jev_clause_ids = [str(item) for item in jev_block.get("clause_ids", [])]
    matched = [
      MatchedClause(
        clause_id=cid,
        section_title=clause_by_id[cid].section_title,
        text=clause_by_id[cid].clause_text,
      )
      for cid in jev_clause_ids if cid in clause_by_id
    ]
    evidence = EvidenceBundle(
      score=confidence,
      matched_clauses=matched,
      quality="HIGH" if matched else "NO_RELIABLE_MATCH",
      has_credited_support=bool(matched),
    )
    elements = []
    qwen_block = _qwen_block(
      comparison_qwen, node, act, title, summary, rule, policy_clauses
    )
    obligations.append(
      _obligation_finding(
        node_id=node.id,
        title=title,
        summary=summary,
        act=act,
        law_status=law_status,
        applicability_reason=decision.reason,
        rule=rule,
        evidence=evidence,
        status=status,
        confidence=confidence,
        elements=elements,
        jev_status=str(jev_block.get("status") or ""),
        jev_clause_ids=jev_clause_ids,
        jev_reason=str(jev_block.get("reason") or ""),
        jev_confidence=float(jev_block.get("confidence") or 0.0),
        qwen_status=str(qwen_block.get("status") or ""),
        qwen_clause_ids=[str(item) for item in qwen_block.get("clause_ids", [])],
        qwen_reason=str(qwen_block.get("reason") or ""),
        qwen_confidence=float(qwen_block.get("confidence") or 0.0),
      )
    )

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
  policy_graph = None
  mapping_failures: list[dict[str, object]] = []
  if policy_builder is not None:
    graph_ir, failures = policy_builder.build(document)
    policy_graph = graph_ir.to_dict()
    mapping_failures = [item.to_dict() for item in failures]
  return AnalysisResult(
    document_id=document.metadata.document_id,
    source_filename=str(document.metadata.filename or ""),
    jurisdiction=code,
    applicable_laws=laws,
    obligations=obligations,
    gaps=gaps,
    penalties=penalties,
    weighted_pct=_weighted_pct([row for row in obligations if row.status != "not_applicable"]),
    policy_graph=policy_graph,
    mapping_failures=mapping_failures,
  )




def _jev_block(client, obligation, act, title, summary, rule, policy_clauses):
    """Call Jev and normalize its fixed answer set."""
    block = client.classify_applicable_duty(
            obligation_id=obligation.id,
            act=act,
            title=title,
            summary=summary,
            requirement_elements=[{"id": e.id, "label": e.label} for e in rule.requirement_elements],
            policy_clauses=policy_clauses,
        )
    status = str(block.get("status") or "").strip().lower()
    if status not in ObligationStatus.__args__:
        status = "undetermined"
    return {
        "status": status,
      "clause_ids": _clause_ids(block),
        "reason": str(block.get("reason") or ""),
      "confidence": _confidence(block),
    }


def _qwen_block(client, obligation, act, title, summary, rule, policy_clauses):
    """Return a normalized optional Qwen comparison answer."""
    try:
      block = client.classify_applicable_duty(
        obligation_id=obligation.id,
        act=act,
        title=title,
        summary=summary,
        requirement_elements=[{"id": e.id, "label": e.label} for e in rule.requirement_elements],
        policy_clauses=policy_clauses,
      )
    except QwenError:
      return {}
    status = str(block.get("status") or "").strip().lower()
    if status not in ObligationStatus.__args__:
      status = "undetermined"
    return {
      "status": status,
      "clause_ids": _clause_ids(block),
      "reason": str(block.get("reason") or ""),
      "confidence": _confidence(block),
    }


def _clause_ids(block: dict[str, object]) -> list[str]:
  raw = block.get("clause_ids", [])
  if not isinstance(raw, (list, tuple)):
    return []
  return [str(item) for item in raw if item]


def _confidence(block: dict[str, object]) -> float:
  try:
    return max(0.0, min(1.0, float(block.get("confidence") or 0.0)))
  except (TypeError, ValueError):
    return 0.0

def _obligation_finding(
  *,
  node_id: str,
  title: str,
  summary: str,
  act: str,
  law_status: str,
  applicability_reason: str,
  rule,
  evidence,
  status: str,
  confidence: float,
  elements,
  extra_cues: list[str] | None = None,
  jev_status: str = "",
  jev_clause_ids: list[str] = None,
  jev_reason: str = "",
  jev_confidence: float = 0.0,
  qwen_status: str = "",
  qwen_clause_ids: list[str] = None,
  qwen_reason: str = "",
  qwen_confidence: float = 0.0,
) -> ObligationFinding:
  row = ObligationFinding(
    obligation_id=node_id,
    title=title,
    summary=summary,
    act=act,
    status=status,
    score=evidence.score,
    matched_clause_ids=[item.clause_id for item in evidence.matched_clauses],
    matched_clauses=evidence.matched_clauses,
    counter_evidence=[
      MatchedClause(
        clause_id=item.clause_id,
        section_title=item.section_title or "",
        text=best_sentence(
          actor_filtered_text(item.clause_text, rule) or item.clause_text,
          rule,
          extra_cues=extra_cues,
        ),
      )
      for item in evidence.contradiction_clauses
    ],
    applicability_reason=applicability_reason,
    law_status=law_status,
    confidence=confidence,
    evidence_quality=evidence.quality,
    elements=elements,
    severity=rule.severity,
    jev_status=jev_status,
    jev_clause_ids=jev_clause_ids or [],
    jev_reason=jev_reason,
    jev_confidence=jev_confidence,
    qwen_status=qwen_status,
    qwen_clause_ids=qwen_clause_ids or [],
    qwen_reason=qwen_reason,
    qwen_confidence=qwen_confidence,
  )
  row.reason = explain_finding(row, evidence)
  return row


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
