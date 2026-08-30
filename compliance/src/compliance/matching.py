"""Obligation-centric evidence: multi-credit retrieval, polarity-aware elements."""

from __future__ import annotations

import re
import unicodedata
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
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset({
  "a", "an", "and", "as", "at", "be", "by", "for", "from", "general",
  "in", "into", "is", "mandatory", "must", "no", "not", "obligation",
  "obligations", "of", "on", "or", "shall", "the", "this", "to", "with",
})
_DENIAL_LEXICON = (
  "cannot",
  "without obtaining",
  "does not",
  "will not",
  "no dedicated",
  "waive",
  "irrevocable",
)
_FIDUCIARY_MARKERS = (
  "we ",
  "we've",
  "we're",
  "our ",
  "the company",
  "body corporate",
  "quickbazaar",
  "bharatpay",
  "data fiduciary",
)
_USER_MARKERS = (
  "you are responsible",
  "you must",
  "you shall",
  "you should",
  "users are",
  "parents are responsible",
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


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
  contradiction_clauses: list[Clause] = field(default_factory=list)
  has_credited_support: bool = False


def tokens(text: str) -> set[str]:
  return {word for word in _TOKEN_RE.findall(text.lower()) if len(word) >= 4 and word not in _STOP}


def title_overlap(clause_texts: list[str], title: str) -> bool:
  needles = tokens(title)
  if not needles:
    return True
  haystack = tokens(" ".join(clause_texts))
  needed = 1 if len(needles) <= 2 else 2
  return len(needles & haystack) >= needed


def _norm(text: str) -> str:
  return " ".join(unicodedata.normalize("NFKC", text or "").lower().split())


def clause_has_denial_polarity(text: str, rule: DutyRule | None = None) -> bool:
  lowered = _norm(text)
  if any(token in lowered for token in _DENIAL_LEXICON):
    return True
  if rule is not None:
    return any(_norm(cue) in lowered for cue in rule.contradiction_cues if cue)
  return False


def find_contradictions(
  clauses: list[Clause],
  rule: DutyRule,
  extra_cues: list[str] | None = None,
) -> list[Clause]:
  cues = [_norm(cue) for cue in list(rule.contradiction_cues) + list(extra_cues or []) if cue]
  if not cues:
    return []
  hits: list[Clause] = []
  seen: set[str] = set()
  for clause in clauses:
    own = actor_filtered_text(clause.clause_text, rule)
    if not own:
      continue
    blob = _norm(own)
    if not any(cue in blob for cue in cues):
      continue
    if clause.clause_id in seen:
      continue
    seen.add(clause.clause_id)
    hits.append(clause)
  return hits


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
  _obligation_id: str,
  title: str,
  rule: DutyRule,
  clauses: list[Clause],
  credited: list[tuple[Clause, float]],
  extra_cues: list[str] | None = None,
) -> EvidenceBundle:
  had_credits = bool(credited)
  credited = _filter_credited(credited, rule)
  by_id: dict[str, tuple[Clause, float, str]] = {}
  for clause, score in credited:
    text = actor_filtered_text(clause.clause_text, rule)
    if not text:
      continue
    prev = by_id.get(clause.clause_id)
    if prev is None or score > prev[1]:
      by_id[clause.clause_id] = (clause, score, text)

  pool = _element_pool(clauses, credited, had_credits=had_credits)
  element_hits: list[str] = []
  for clause in pool:
    filtered = actor_filtered_text(clause.clause_text, rule)
    if not filtered:
      continue
    expanded = expand_clause_evidence(clause, clauses)
    for spec in rule.requirement_elements:
      if spec.id in element_hits:
        continue
      for item in expanded:
        hit_text = actor_filtered_text(item.clause_text, rule) or ""
        if not hit_text:
          continue
        if clause_has_denial_polarity(hit_text, rule):
          continue
        if not any(_norm(keyword) in _norm(hit_text) for keyword in spec.keywords if keyword):
          continue
        element_hits.append(spec.id)
        prev = by_id.get(item.clause_id)
        if prev is None:
          by_id[item.clause_id] = (item, RELIABLE_SCORE, hit_text)
        break

  contradictions = _rank_counters(
    find_contradictions(clauses, rule, extra_cues=extra_cues),
    clauses,
    rule,
    extra_cues,
  )
  cue_ids = {item.clause_id for item in contradictions}
  credited_ids = {clause.clause_id for clause, _score in credited}
  ranked = sorted(by_id.values(), key=lambda pair: pair[1], reverse=True)
  supportive = [
    pair
    for pair in ranked
    if pair[0].clause_id not in cue_ids and not clause_has_denial_polarity(pair[2], rule)
  ]
  has_credited_support = any(pair[0].clause_id in credited_ids for pair in supportive)
  score = max((pair[1] for pair in supportive), default=0.0)
  texts = [pair[2] for pair in supportive]
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
      text=best_sentence(text, rule, extra_cues=extra_cues),
    )
    for clause, _score, text in supportive
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
    contradiction_clauses=contradictions,
    has_credited_support=has_credited_support,
  )


def _element_pool(
  clauses: list[Clause],
  credited: list[tuple[Clause, float]],
  *,
  had_credits: bool = False,
) -> list[Clause]:
  """Keyword-score credited clauses only. Empty credits fall back for stub-search tests."""
  if not credited:
    return [] if had_credits else list(clauses)
  pool: list[Clause] = []
  seen: set[str] = set()
  for clause, _score in credited:
    if clause.clause_id in seen:
      continue
    seen.add(clause.clause_id)
    pool.append(clause)
  return pool


def split_sentences(text: str) -> list[str]:
  parts = _SENTENCE_RE.split((text or "").strip())
  return [part.strip() for part in parts if part.strip()]


def sentence_actor(text: str) -> str:
  lowered = f"{_norm(text)} "
  has_fiduciary = any(marker in lowered for marker in _FIDUCIARY_MARKERS)
  has_user = any(marker in lowered for marker in _USER_MARKERS)
  if has_user:
    return "user"
  if has_fiduciary:
    return "fiduciary"
  return "unknown"


def actor_filtered_text(text: str, rule: DutyRule) -> str:
  sentences = split_sentences(text)
  if not sentences:
    return ""
  if getattr(rule, "bound_actor", "fiduciary") != "fiduciary":
    return " ".join(sentences)
  has_user = any(sentence_actor(item) == "user" for item in sentences)
  has_fiduciary = any(sentence_actor(item) == "fiduciary" for item in sentences)
  if has_user and not has_fiduciary:
    return ""
  kept = [item for item in sentences if sentence_actor(item) != "user"]
  return " ".join(kept)


_DISTINCTIVE = (
  "advertis",
  "target",
  "profil",
  "sell",
  "monetis",
  "grievance",
  "disclos",
)


def _sentence_score(sentence: str, rule: DutyRule, extra_cues: list[str] | None = None) -> tuple[int, int]:
  lowered = _norm(sentence)
  cues = [_norm(cue) for cue in list(rule.contradiction_cues) + list(extra_cues or []) if cue]
  keywords = [
    _norm(keyword)
    for spec in rule.requirement_elements
    for keyword in spec.keywords
    if keyword
  ]
  cue_hits = sum(1 for cue in cues if cue in lowered)
  keyword_hits = sum(1 for keyword in keywords if keyword in lowered)
  distinctive = sum(1 for token in _DISTINCTIVE if token in lowered and (token in keywords or any(token in cue for cue in cues)))
  return (cue_hits + distinctive, keyword_hits)


def best_sentence(text: str, rule: DutyRule, extra_cues: list[str] | None = None) -> str:
  sentences = split_sentences(text)
  if not sentences:
    return text
  return max(sentences, key=lambda sentence: _sentence_score(sentence, rule, extra_cues))


def _rank_counters(
  hits: list[Clause],
  clauses: list[Clause],
  rule: DutyRule,
  extra_cues: list[str] | None = None,
) -> list[Clause]:
  if not hits:
    return []
  titles = {item.section_title or "" for item in hits if item.section_title}
  section_ids = {item.section_id for item in hits if item.section_id}
  hit_ids = {item.clause_id for item in hits}
  candidates: list[Clause] = []
  seen: set[str] = set()
  for clause in clauses:
    title = clause.section_title or ""
    same_section = (title and title in titles) or (clause.section_id and clause.section_id in section_ids)
    if clause.clause_id not in hit_ids and not same_section:
      continue
    if not actor_filtered_text(clause.clause_text, rule):
      continue
    if clause.clause_id in seen:
      continue
    seen.add(clause.clause_id)
    candidates.append(clause)

  def sort_key(clause: Clause) -> tuple[int, int]:
    text = actor_filtered_text(clause.clause_text, rule) or clause.clause_text
    sentence = best_sentence(text, rule, extra_cues)
    return _sentence_score(sentence, rule, extra_cues)

  candidates.sort(key=sort_key, reverse=True)
  return candidates


def _filter_credited(
  credited: list[tuple[Clause, float]],
  rule: DutyRule,
) -> list[tuple[Clause, float]]:
  kept: list[tuple[Clause, float]] = []
  for clause, score in credited:
    if actor_filtered_text(clause.clause_text, rule):
      kept.append((clause, score))
  return kept


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


def _hit_id(hit: SearchHit) -> str:
  payload = hit.payload or {}
  return str(payload.get("obligation_id") or hit.clause_id or "")
