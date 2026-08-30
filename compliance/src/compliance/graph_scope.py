"""In-process GraphIR scope for /analyze: Obligation nodes + PENALIZES walk."""

from __future__ import annotations

from pathlib import Path

from graph_builder.catalog_ir import (
  CatalogObligation,
  CatalogPenalty,
  CatalogRequirement,
  catalog_to_graph_ir,
)
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from compliance.catalog import LawCatalog, load_catalog
from compliance.duty_rules import resolve_duty_rule
from compliance.models import ObligationFinding, PenaltyFinding


def ir_from_catalog(catalog: LawCatalog) -> GraphIR:
  duties = [
    CatalogObligation(
      obligation_id=chunk.doc_id,
      title=chunk.title,
      text=chunk.clause_text,
      act=chunk.act,
      chunk_type=chunk.chunk_type,
      summary=chunk.summary,
      entity_ids=tuple(chunk.entity_ids),
    )
    for chunk in catalog.obligations
  ]
  penalties = [
    CatalogPenalty(
      penalty_id=row.penalty_id,
      title=row.title,
      summary=row.summary,
      act=row.act,
      obligation_ids=row.obligation_ids,
      amount_crore=row.amount_crore,
      imprisonment_years=row.imprisonment_years,
    )
    for row in catalog.penalties
  ]
  requirements: list[CatalogRequirement] = []
  for chunk in catalog.obligations:
    rule = resolve_duty_rule(chunk.doc_id, catalog_roles=tuple(chunk.entity_ids))
    for spec in rule.requirement_elements:
      requirements.append(
        CatalogRequirement(
          obligation_id=chunk.doc_id,
          element_id=spec.id,
          label=spec.label,
        )
      )
  return catalog_to_graph_ir(duties, penalties, requirements)


def ir_from_paths(paths: list[Path]) -> GraphIR:
  return ir_from_catalog(load_catalog(paths))


def obligation_nodes(ir: GraphIR) -> list[GraphNode]:
  return [node for node in ir.nodes if node.label == "Obligation"]


def penalties_for(ir: GraphIR, obligation_id: str) -> list[CatalogPenalty]:
  """Penalties that PENALIZES the given Obligation node."""
  penalty_nodes = {node.id: node for node in ir.nodes if node.label == "Penalty"}
  found: list[CatalogPenalty] = []
  seen: set[str] = set()
  for rel in ir.relationships:
    if rel.type != "PENALIZES" or rel.target != obligation_id:
      continue
    node = penalty_nodes.get(rel.source)
    if node is None or node.id in seen:
      continue
    seen.add(node.id)
    props = node.properties or {}
    found.append(
      CatalogPenalty(
        penalty_id=node.id,
        title=str(props.get("title") or node.id),
        summary=str(props.get("summary") or ""),
        act=str(props.get("act") or ""),
        obligation_ids=(obligation_id,),
        amount_crore=_float_or_none(props.get("amount_crore")),
        imprisonment_years=_float_or_none(props.get("imprisonment_years")),
      )
    )
  return found


def attach_evidence(
  ir: GraphIR,
  findings: list[ObligationFinding],
  penalties: list[PenaltyFinding] | None = None,
) -> GraphIR:
  """Copy IR and add MATCHED_BY / SUPPORTED_BY / CONFLICTS_WITH / MAY_TRIGGER."""
  nodes = list(ir.nodes)
  relationships = list(ir.relationships)
  seen_clause: set[str] = set()
  for finding in findings:
    if finding.evidence_quality in {"HIGH", "MEDIUM"}:
      for clause in finding.matched_clauses:
        relationships.append(
          GraphRelationship(
            source=finding.obligation_id,
            target=clause.clause_id,
            type="MATCHED_BY",
          )
        )
        if clause.clause_id not in seen_clause:
          nodes.append(GraphNode(id=clause.clause_id, label="Clause", properties={"text": clause.text}))
          seen_clause.add(clause.clause_id)
    for element in finding.elements:
      if not element.satisfied:
        continue
      eid = f"{finding.obligation_id}::{element.id}"
      for clause in finding.matched_clauses:
        relationships.append(
          GraphRelationship(source=eid, target=clause.clause_id, type="SUPPORTED_BY")
        )
    if finding.status == "violation":
      for clause in finding.matched_clauses:
        relationships.append(
          GraphRelationship(source=clause.clause_id, target=finding.obligation_id, type="CONFLICTS_WITH")
        )
  for row in penalties or []:
    if row.eligibility != "may_trigger":
      continue
    relationships.append(
      GraphRelationship(source=row.obligation_id, target=row.title, type="MAY_TRIGGER")
    )
  return GraphIR(nodes=nodes, relationships=relationships)


def _float_or_none(value: object) -> float | None:
  if value is None or value is False:
    return None
  try:
    return float(value)  # type: ignore[arg-type]
  except (TypeError, ValueError):
    return None
