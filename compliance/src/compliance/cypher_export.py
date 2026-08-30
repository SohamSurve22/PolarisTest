"""Cypher strings from GraphIR + findings. Never executed against Neo4j at /analyze."""

from __future__ import annotations

from graph_builder.graph_ir import GraphIR

from compliance.graph_scope import attach_evidence
from compliance.models import ObligationFinding, PenaltyFinding


def export_cypher(
  ir: GraphIR,
  findings: list[ObligationFinding] | None = None,
  penalties: list[PenaltyFinding] | None = None,
) -> str:
  enriched = attach_evidence(ir, findings or [], penalties)
  lines = [
    "// Applicability (runtime uses applicability.py; this is documentation only)",
    "MATCH (e:Entity)-[:HAS_ROLE]->(r)-[:MAY_HAVE]->(o:Obligation) RETURN e, r, o",
  ]
  for rel in enriched.relationships:
    if rel.type == "MATCHED_BY":
      lines.append(
        f"MATCH (o:Obligation {{id: '{_esc(rel.source)}'}})-[:MATCHED_BY]->"
        f"(c:Clause {{id: '{_esc(rel.target)}'}})"
      )
    elif rel.type == "HAS_REQUIREMENT":
      lines.append(
        f"MATCH (o:Obligation {{id: '{_esc(rel.source)}'}})-[:HAS_REQUIREMENT]->"
        f"(e:RequirementElement {{id: '{_esc(rel.target)}'}})"
      )
    elif rel.type == "SUPPORTED_BY":
      lines.append(
        f"MATCH (e:RequirementElement {{id: '{_esc(rel.source)}'}})-[:SUPPORTED_BY]->"
        f"(c:Clause {{id: '{_esc(rel.target)}'}})"
      )
    elif rel.type == "CONFLICTS_WITH":
      lines.append(
        f"MATCH (c:Clause {{id: '{_esc(rel.source)}'}})-[:CONFLICTS_WITH]->"
        f"(o:Obligation {{id: '{_esc(rel.target)}'}})"
      )
    elif rel.type == "MAY_TRIGGER":
      lines.append(
        f"MATCH (o:Obligation {{id: '{_esc(rel.source)}'}})-[:MAY_TRIGGER]->(p:Penalty)"
      )
  return "\n".join(lines) + "\n"


def _esc(value: str) -> str:
  return value.replace("\\", "\\\\").replace("'", "\\'")
