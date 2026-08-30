"""Lift a duty catalog into GraphIR Obligation / Penalty nodes.

Does not import compliance. Callers map LawCatalog rows into the dataclasses here.
"""

from __future__ import annotations

from dataclasses import dataclass

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship


@dataclass(frozen=True)
class CatalogObligation:
  obligation_id: str
  title: str
  text: str = ""
  act: str = ""
  chunk_type: str | None = None
  summary: str = ""
  section_id: str | None = None
  entity_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CatalogPenalty:
  penalty_id: str
  title: str
  summary: str = ""
  act: str = ""
  obligation_ids: tuple[str, ...] = ()
  amount_crore: float | None = None
  imprisonment_years: float | None = None


@dataclass(frozen=True)
class CatalogRequirement:
  obligation_id: str
  element_id: str
  label: str


def catalog_to_graph_ir(
  obligations: list[CatalogObligation],
  penalties: list[CatalogPenalty] | None = None,
  requirements: list[CatalogRequirement] | None = None,
) -> GraphIR:
  """Build LawVersion → Obligation (+ Penalty -PENALIZES-> Obligation) GraphIR."""
  nodes: list[GraphNode] = []
  relationships: list[GraphRelationship] = []
  seen_acts: set[str] = set()
  duty_ids: set[str] = set()

  for duty in obligations:
    oid = duty.obligation_id.strip()
    if not oid:
      continue
    act = (duty.act or "").strip()
    if act and act not in seen_acts:
      seen_acts.add(act)
      nodes.append(
        GraphNode(
          id=act,
          label="LawVersion",
          properties={"code": act},
        )
      )
    body = (duty.text or "").strip() or (duty.summary or "").strip()
    props: dict[str, object] = {
      "title": duty.title,
      "text": body,
      "summary": duty.summary,
      "act": act,
    }
    if duty.chunk_type:
      props["chunk_type"] = duty.chunk_type
    if duty.section_id:
      props["section_id"] = duty.section_id
    if duty.entity_ids:
      props["entity_ids"] = list(duty.entity_ids)
    nodes.append(GraphNode(id=oid, label="Obligation", properties=props))
    duty_ids.add(oid)
    if act:
      relationships.append(
        GraphRelationship(source=act, target=oid, type="HAS_OBLIGATION")
      )

  for pen in penalties or []:
    pid = pen.penalty_id.strip()
    if not pid:
      continue
    targets = tuple(oid for oid in pen.obligation_ids if oid in duty_ids)
    if not targets:
      continue
    nodes.append(
      GraphNode(
        id=pid,
        label="Penalty",
        properties={
          "title": pen.title,
          "summary": pen.summary,
          "act": pen.act,
          "amount_crore": pen.amount_crore,
          "imprisonment_years": pen.imprisonment_years,
        },
      )
    )
    for oid in targets:
      relationships.append(GraphRelationship(source=pid, target=oid, type="PENALIZES"))

  for req in requirements or []:
    oid = req.obligation_id.strip()
    if oid not in duty_ids or not req.element_id:
      continue
    eid = f"{oid}::{req.element_id}"
    nodes.append(
      GraphNode(
        id=eid,
        label="RequirementElement",
        properties={"label": req.label, "obligation_id": oid, "element_id": req.element_id},
      )
    )
    relationships.append(GraphRelationship(source=oid, target=eid, type="HAS_REQUIREMENT"))

  return GraphIR(nodes=nodes, relationships=relationships)
