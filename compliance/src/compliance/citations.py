"""Closest policy citation for a finding. LLM does not choose the snippet."""

from __future__ import annotations

from compliance.models import ObligationFinding, MatchedClause

_SNIPPET = 180


def closest_citation(row: ObligationFinding, *, snippet: int = _SNIPPET) -> str:
  """Primary snippet: counter-evidence for violation/conflict, else first match."""
  first = _primary_match(row)
  if first is None:
    if row.evidence_quality == "NO_RELIABLE_MATCH":
      return "No reliable evidence found"
    return "No matching clause"
  heading = first.section_title or first.clause_id
  text = " ".join(str(first.text or "").split())
  if len(text) > snippet:
    text = f"{text[:snippet].rstrip()}..."
  if heading and text:
    return f"{heading}: {text}"
  return heading or text or "No matching clause"


def primary_match(row: ObligationFinding) -> MatchedClause | None:
  return _primary_match(row)


def _primary_match(row: ObligationFinding) -> MatchedClause | None:
  if row.status in {"violation", "conflict"} and row.counter_evidence:
    return row.counter_evidence[0]
  if row.matched_clauses:
    return row.matched_clauses[0]
  if row.counter_evidence:
    return row.counter_evidence[0]
  return None
