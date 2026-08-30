"""Resolve policy-internal section pointers into extra evidence clauses."""

from __future__ import annotations

import re

from document_pipeline.models.clause import Clause

_SECTION_REF = re.compile(
  r"(?i)\b(?:as\s+described\s+in\s+|see(?:\s+also)?\s+)?section\s+(\d+)\b",
)
_GENERIC = re.compile(
  r"(?i)\b(?:all\s+)?applicable\s+laws?(?:\s+and\s+timelines)?|"
  r"as\s+required\s+by\s+law|"
  r"applicable\s+legal\s+requirements|"
  r"as\s+required\s+by\s+applicable\s+law\b",
)


def expand_clause_evidence(clause: Clause, all_clauses: list[Clause]) -> list[Clause]:
  """Return the clause plus bodies of referenced policy sections."""
  numbers = {match.group(1) for match in _SECTION_REF.finditer(clause.clause_text or "")}
  found = [clause]
  seen = {clause.clause_id}
  if not numbers:
    return found
  for other in all_clauses:
    if other.clause_id in seen:
      continue
    if _section_matches(other, numbers):
      found.append(other)
      seen.add(other.clause_id)
  return found


def has_generic_legal_language(text: str, phrases: list[str] | None = None) -> bool:
  blob = text or ""
  if _GENERIC.search(blob):
    return True
  lowered = blob.lower()
  for phrase in phrases or ():
    if phrase and phrase.lower() in lowered:
      return True
  return False


def _section_matches(clause: Clause, numbers: set[str]) -> bool:
  title = (clause.section_title or "").lower()
  section_id = (clause.section_id or "").lower()
  for number in numbers:
    if re.search(rf"(?i)(?:^|\b)(?:section\s+)?{re.escape(number)}(?:\b|[\.:])", title):
      return True
    if section_id.endswith(number.zfill(3)) or section_id.endswith(number):
      return True
  return False
