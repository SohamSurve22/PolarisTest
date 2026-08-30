"""India/DPDP analysis: GraphIR duties scored against policy clauses via Qdrant."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.semantic import StructuralRole
from vectorization.models import SearchHit
from vectorization.sources import clause_from_entity

from compliance.graph_scope import ir_from_paths, obligation_nodes, penalties_for
from compliance.models import (
  AnalysisResult,
  GapFinding,
  MatchedClause,
  ObligationFinding,
  PenaltyFinding,
)

COVERED_SCORE = 0.55
PARTIAL_SCORE = 0.30
SUPPORTED_JURISDICTIONS = frozenset({"IN", "INDIA", "IN-DPDP"})
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset({
  "a", "an", "and", "as", "at", "be", "by", "for", "from", "general",
  "in", "into", "is", "mandatory", "must", "no", "not", "obligation",
  "obligations", "of", "on", "or", "shall", "the", "this", "to", "with",
})

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
) -> AnalysisResult:
  code = (jurisdiction or "IN").strip().upper()
  if code not in SUPPORTED_JURISDICTIONS:
    msg = f"Unsupported jurisdiction: {jurisdiction}"
    raise ValueError(msg)

  ir = ir_from_paths(law_paths)
  duties = obligation_nodes(ir)
  search_fn = search or default_search
  clauses = _policy_clauses(document)
  best: dict[str, tuple[float, list[MatchedClause]]] = {
    node.id: (0.0, []) for node in duties
  }

  try:
    for clause in clauses:
      hits = [
        hit
        for hit in search_fn(clause.clause_text)
        if _hit_obligation_id(hit) in best
      ]
      if not hits:
        continue
      hit = max(hits, key=lambda item: item.score)
      oid = _hit_obligation_id(hit)
      score, matches = best[oid]
      found = list(matches)
      if clause.clause_id not in {row.clause_id for row in found}:
        found.append(
          MatchedClause(
            clause_id=clause.clause_id,
            section_title=clause.section_title or "",
            text=clause.clause_text,
          )
        )
      if hit.score > score:
        best[oid] = (hit.score, found)
      else:
        best[oid] = (score, found)
  except ValueError:
    raise
  except Exception as exc:
    raise AnalyzeError(str(exc)) from exc

  obligations: list[ObligationFinding] = []
  for node in duties:
    score, matches = best[node.id]
    props = node.properties or {}
    title = str(props.get("title") or node.id)
    summary = str(props.get("summary") or "")
    act = str(props.get("act") or "")
    status = _status(score, [row.text for row in matches], title)
    obligations.append(
      ObligationFinding(
        obligation_id=node.id,
        title=title,
        summary=summary,
        act=act,
        status=status,
        score=score,
        matched_clause_ids=[row.clause_id for row in matches],
        matched_clauses=matches,
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
    if row.status != "covered"
  ]

  penalties: list[PenaltyFinding] = []
  seen: set[tuple[str, str]] = set()
  for row in obligations:
    if row.status == "covered":
      continue
    for link in penalties_for(ir, row.obligation_id):
      key = (link.penalty_id, row.obligation_id)
      if key in seen:
        continue
      seen.add(key)
      penalties.append(
        PenaltyFinding(
          obligation_id=row.obligation_id,
          title=link.title,
          amount_crore=link.amount_crore,
          imprisonment_years=link.imprisonment_years,
          summary=link.summary,
          act=link.act,
        )
      )

  laws = sorted({row.act for row in obligations if row.act})
  return AnalysisResult(
    document_id=document.metadata.document_id,
    source_filename=str(document.metadata.filename or ""),
    jurisdiction=code,
    applicable_laws=laws,
    obligations=obligations,
    gaps=gaps,
    penalties=penalties,
  )


def _status(score: float, clause_texts: list[str], title: str) -> str:
  if score >= COVERED_SCORE and _title_overlap(clause_texts, title):
    return "covered"
  if score >= PARTIAL_SCORE:
    return "partial"
  return "missing"


def _title_overlap(clause_texts: list[str], title: str) -> bool:
  needles = _tokens(title)
  if not needles:
    return True
  haystack = _tokens(" ".join(clause_texts))
  needed = 1 if len(needles) <= 2 else 2
  return len(needles & haystack) >= needed


def _tokens(text: str) -> set[str]:
  return {word for word in _TOKEN_RE.findall(text.lower()) if len(word) >= 4 and word not in _STOP}


def _hit_obligation_id(hit: SearchHit) -> str:
  payload = hit.payload or {}
  return str(payload.get("obligation_id") or hit.clause_id or "")


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
