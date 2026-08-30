"""In-process GraphIR scope for /analyze: Obligation nodes + PENALIZES walk."""

from __future__ import annotations

from pathlib import Path

from graph_builder.catalog_ir import CatalogObligation, CatalogPenalty, catalog_to_graph_ir
from graph_builder.graph_ir import GraphIR, GraphNode

from compliance.catalog import LawCatalog, load_catalog


def ir_from_catalog(catalog: LawCatalog) -> GraphIR:
  duties = [
    CatalogObligation(
      obligation_id=chunk.doc_id,
      title=chunk.title,
      text=chunk.clause_text,
      act=chunk.act,
      chunk_type=chunk.chunk_type,
      summary=chunk.summary,
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
  return catalog_to_graph_ir(duties, penalties)


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


def _float_or_none(value: object) -> float | None:
  if value is None or value is False:
    return None
  try:
    return float(value)  # type: ignore[arg-type]
  except (TypeError, ValueError):
    return None
