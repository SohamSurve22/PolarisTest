"""India/DPDP analysis: match parsed clauses to catalog obligations via Qdrant."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.semantic import StructuralRole
from vectorization.models import SearchHit
from vectorization.sources import clause_from_entity

from compliance.catalog import LawCatalog, load_catalog
from compliance.models import (
  AnalysisResult,
  GapFinding,
  ObligationFinding,
  PenaltyFinding,
)

COVERED_SCORE = 0.55
PARTIAL_SCORE = 0.30
SUPPORTED_JURISDICTIONS = frozenset({"IN", "INDIA", "IN-DPDP"})

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

  catalog = load_catalog(law_paths)
  search_fn = search or default_search
  clauses = _policy_clauses(document)
  best: dict[str, tuple[float, list[str]]] = {
    chunk.doc_id: (0.0, []) for chunk in catalog.obligations
  }

  try:
    for clause in clauses:
      hits = search_fn(clause.clause_text)
      for hit in hits:
        oid = _hit_obligation_id(hit)
        if oid not in best:
          continue
        score, matched = best[oid]
        ids = list(matched)
        if clause.clause_id not in ids:
          ids.append(clause.clause_id)
        if hit.score > score:
          best[oid] = (hit.score, ids)
        else:
          best[oid] = (score, ids)
  except ValueError:
    raise
  except Exception as exc:
    raise AnalyzeError(str(exc)) from exc

  obligations: list[ObligationFinding] = []
  for chunk in catalog.obligations:
    score, matched_ids = best[chunk.doc_id]
    status = _status(score)
    obligations.append(
      ObligationFinding(
        obligation_id=chunk.doc_id,
        title=chunk.title,
        summary=chunk.summary,
        act=chunk.act,
        status=status,
        score=score,
        matched_clause_ids=matched_ids,
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
    for link in catalog.penalties_for(row.obligation_id):
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

  laws = sorted({chunk.act for chunk in catalog.obligations if chunk.act})
  return AnalysisResult(
    document_id=document.metadata.document_id,
    jurisdiction=code,
    applicable_laws=laws,
    obligations=obligations,
    gaps=gaps,
    penalties=penalties,
  )


def _status(score: float) -> str:
  if score >= COVERED_SCORE:
    return "covered"
  if score >= PARTIAL_SCORE:
    return "partial"
  return "missing"


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
