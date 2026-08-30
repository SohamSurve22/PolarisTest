"""Obligation-centric evidence: multi-credit retrieval, elements, specificity."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from document_pipeline.models.clause import Clause
from vectorization.models import SearchHit

from compliance.duty_rules import DutyRule
from compliance.models import MatchedClause
from compliance.references import expand_clause_evidence, has_generic_legal_language

COVERED_SCORE = 0.55
PARTIAL_SCORE = 0.30
RELIABLE_SCORE = 0.40

from document_pipeline.models.clause import Clause
from vectorization.models import SearchHit

from compliance.duty_rules import DutyRule
from compliance.models import MatchedClause
from compliance.references import expand_clause_evidence, has_generic_legal_language

COVERED_SCORE = 0.55
PARTIAL_SCORE = 0.30
RELIABLE_SCORE = 0.40
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset({
  "a", "an", "and", "as", "at", "be", "by", "for", "from", "general",
  "in", "into", "is", "mandatory", "must", "no", "not", "obligation",
  "obligations", "of", "on", "or", "shall", "the", "this", "to", "with",
})


@dataclass
class EvidenceBundle:
  score: float = 0.0
  matched_clauses: list[MatchedClause] = field(default_factory=list)
  quality: str = "NO_RELIABLE_MATCH"
  element_hits: list[str] = field(default_factory=list)
  generic_only: bool = False
  exact_term_hit: bool = False
  title_overlap: bool = False
  expanded_texts: list[str] = field(default_factory=list)


def tokens(text: str) -> set[str]:
  return {word for word in _TOKEN_RE.findall(text.lower()) if len(word) >= 4 and word not in _STOP}


def title_overlap(clause_texts: list[str], title: str) -> bool:
  needles = tokens(title)
  if not needles:
    return True
  haystack = tokens(" ".join(clause_texts))
  needed = 1 if len(needles) <= 2 else 2
  return len(needles & haystack) >= needed


def collect_credits(
  clauses: list[Clause],
  search_fn: Callable[[str], list[SearchHit]],
  scored_ids: set[str],
) -> dict[str, list[tuple[Clause, float]]]:
  """Map obligation id → (clause, score) for every hit at or above PARTIAL_SCORE."""
  credited: dict[str, list[tuple[Clause, float]]] = {oid: [] for oid in scored_ids}
  for clause in clauses:
    hits = [
      hit
      for hit in search_fn(clause.clause_text)
      if _hit_id(hit) in scored_ids and hit.score >= PARTIAL_SCORE
    ]
    seen: set[str] = set()
    for hit in hits:
      oid = _hit_id(hit)
      if oid in seen:
        continue
      seen.add(oid)
      credited[oid].append((clause, hit.score))
  return credited


def gather_evidence(
  obligation_id: str,
  title: str,
  rule: DutyRule,
  clauses: list[Clause],
  credited: list[tuple[Clause, float]],
) -> EvidenceBundle:
  by_id: dict[str, tuple[Clause, float]] = {}
  for clause, score in credited:
    prev = by_id.get(clause.clause_id)
    if prev is None or score > prev[1]:
      by_id[clause.clause_id] = (clause, score)

  element_hits: list[str] = []
  for clause in clauses:
    expanded = expand_clause_evidence(clause, clauses)
    blob = " ".join(item.clause_text for item in expanded)
    lowered = blob.lower()
    for spec in rule.requirement_elements:
      if spec.id in element_hits:
        continue
      if any(keyword.lower() in lowered for keyword in spec.keywords if keyword):
        element_hits.append(spec.id)
        best_clause = max(expanded, key=lambda item: _keyword_count(item.clause_text, spec.keywords))
        prev = by_id.get(best_clause.clause_id)
        if prev is None:
          by_id[best_clause.clause_id] = (best_clause, RELIABLE_SCORE)
        for item in expanded:
          if item.clause_id not in by_id:
            by_id[item.clause_id] = (item, RELIABLE_SCORE)

  ranked = sorted(by_id.values(), key=lambda pair: pair[1], reverse=True)
  score = max((pair[1] for pair in ranked), default=0.0)
  texts = [pair[0].clause_text for pair in ranked]
  overlap = title_overlap(texts, title) if texts else False
  exact = _has_exact_terms(texts, rule.exact_terms)
  generic = bool(texts) and all(
    has_generic_legal_language(text, rule.generic_phrases) for text in texts
  ) and not exact and not element_hits

  quality = _quality(score, overlap, element_hits)
  matches = [
    MatchedClause(
      clause_id=clause.clause_id,
      section_title=clause.section_title or "",
      text=clause.clause_text,
    )
    for clause, _score in ranked
  ]
  if quality == "NO_RELIABLE_MATCH":
    matches = []
  return EvidenceBundle(
    score=score,
    matched_clauses=matches,
    quality=quality,
    element_hits=element_hits,
    generic_only=generic,
    exact_term_hit=exact,
    title_overlap=overlap,
    expanded_texts=texts,
  )


def _quality(score: float, overlap: bool, element_hits: list[str]) -> str:
  if element_hits or overlap:
    if score >= COVERED_SCORE:
      return "HIGH"
    if score >= RELIABLE_SCORE or element_hits:
      return "MEDIUM"
    if score >= PARTIAL_SCORE:
      return "LOW"
  elif score >= RELIABLE_SCORE:
    return "MEDIUM"
  return "NO_RELIABLE_MATCH"


def _has_exact_terms(texts: list[str], terms: list[str]) -> bool:
  blob = " ".join(texts).lower()
  return any(term.lower() in blob for term in terms if term)


def _keyword_count(text: str, keywords: list[str]) -> int:
  lowered = text.lower()
  return sum(1 for keyword in keywords if keyword and keyword.lower() in lowered)


def _hit_id(hit: SearchHit) -> str:
  payload = hit.payload or {}
  return str(payload.get("obligation_id") or hit.clause_id or "")
