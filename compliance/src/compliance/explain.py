"""Engine-owned why-copy for findings. Not model-generated."""

from __future__ import annotations

from compliance.matching import EvidenceBundle
from compliance.models import ObligationFinding


def explain_finding(row: ObligationFinding, evidence: EvidenceBundle | None = None) -> str:
  statute = f"{row.act}: {row.title}".strip(": ") if row.act else row.title
  if row.status == "not_applicable":
    return row.applicability_reason or "This obligation does not apply to this entity, role, or document."
  if row.status == "violation":
    snippet = _counter_snippet(row, evidence)
    if snippet:
      return f"Policy text directly conflicts with {statute}: {snippet}"
    return f"Policy text directly conflicts with {statute}."
  if row.status == "conflict":
    return f"This policy contains contradictory clauses about {statute}."
  if row.status == "undetermined":
    return (
      f"Evidence for {statute} is too generic or weak to classify coverage. "
      "A statement that the organisation complies with applicable law is not proof of compliance."
    )
  if row.status == "covered":
    return f"Policy clauses satisfy {statute}."
  if row.status == "partial":
    hits = [item.label for item in row.elements if item.satisfied]
    missing = [item.label for item in row.elements if not item.satisfied]
    if hits and missing:
      return (
        f"Policy addresses {', '.join(hits)} for {statute}, "
        f"but not {', '.join(missing)}."
      )
    return f"Closest policy text is related, but it does not clearly cover {statute}."
  if evidence is not None and evidence.quality == "NO_RELIABLE_MATCH":
    return "No reliable evidence found."
  return "No sufficient policy evidence maps to this duty. Missing policy language is not a finding of legal violation."


def _counter_snippet(row: ObligationFinding, evidence: EvidenceBundle | None) -> str:
  text = ""
  if evidence is not None and evidence.contradiction_clauses:
    text = evidence.contradiction_clauses[0].clause_text or ""
  elif row.counter_evidence:
    text = row.counter_evidence[0].text or ""
  return " ".join(text.split())
