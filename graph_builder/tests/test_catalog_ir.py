from __future__ import annotations

from graph_builder.catalog_ir import CatalogObligation, CatalogPenalty, CatalogRequirement, catalog_to_graph_ir
from graph_builder.kg_export import graph_ir_to_kg_dict


def test_two_acts_two_duties() -> None:
  ir = catalog_to_graph_ir(
    [
      CatalogObligation(
        obligation_id="DPDP_SEC_4_SUB_1",
        title="Notice",
        text="Give notice before processing.",
        act="DPDP",
        chunk_type="obligation",
      ),
      CatalogObligation(
        obligation_id="SPDI_R5",
        title="Consent",
        text="Obtain consent for SPDI.",
        act="SPDI_RULES_2011",
        chunk_type="obligation",
      ),
    ]
  )
  by_id = {node.id: node for node in ir.nodes}
  assert by_id["DPDP"].label == "LawVersion"
  assert by_id["DPDP"].properties["code"] == "DPDP"
  assert by_id["SPDI_RULES_2011"].label == "LawVersion"
  assert by_id["DPDP_SEC_4_SUB_1"].label == "Obligation"
  assert by_id["DPDP_SEC_4_SUB_1"].properties["text"] == "Give notice before processing."
  assert by_id["DPDP_SEC_4_SUB_1"].properties["title"] == "Notice"
  assert by_id["SPDI_R5"].label == "Obligation"
  rels = {(rel.source, rel.target, rel.type) for rel in ir.relationships}
  assert ("DPDP", "DPDP_SEC_4_SUB_1", "HAS_OBLIGATION") in rels
  assert ("SPDI_RULES_2011", "SPDI_R5", "HAS_OBLIGATION") in rels


def test_obligation_text_falls_back_to_summary() -> None:
  ir = catalog_to_graph_ir(
    [
      CatalogObligation(
        obligation_id="X1",
        title="Duty",
        text="",
        summary="Plain English duty.",
        act="DPDP",
      )
    ]
  )
  node = next(n for n in ir.nodes if n.label == "Obligation")
  assert node.properties["text"] == "Plain English duty."


def test_penalty_penalizes_listed_obligations() -> None:
  ir = catalog_to_graph_ir(
    [
      CatalogObligation(
        obligation_id="DPDP_SEC_8",
        title="Safeguards",
        text="Implement safeguards.",
        act="DPDP",
      )
    ],
    [
      CatalogPenalty(
        penalty_id="DPDP_PEN_8",
        title="Fine",
        summary="Up to 250 crore.",
        act="DPDP",
        obligation_ids=("DPDP_SEC_8",),
        amount_crore=250.0,
        imprisonment_years=None,
      )
    ],
  )
  pen = next(n for n in ir.nodes if n.label == "Penalty")
  assert pen.id == "DPDP_PEN_8"
  assert pen.properties["amount_crore"] == 250.0
  assert any(
    rel.source == "DPDP_PEN_8" and rel.target == "DPDP_SEC_8" and rel.type == "PENALIZES"
    for rel in ir.relationships
  )


def test_penalty_skipped_when_no_matching_obligation() -> None:
  ir = catalog_to_graph_ir(
    [
      CatalogObligation(
        obligation_id="DPDP_SEC_8",
        title="Safeguards",
        text="Implement safeguards.",
        act="DPDP",
      )
    ],
    [
      CatalogPenalty(
        penalty_id="ORPHAN",
        title="Orphan",
        obligation_ids=("MISSING_ID",),
      )
    ],
  )
  assert not any(n.label == "Penalty" for n in ir.nodes)


def test_requirement_element_has_requirement_edge() -> None:
  ir = catalog_to_graph_ir(
    [
      CatalogObligation(
        obligation_id="DPDP_SEC_8_SUB_5",
        title="Safeguards",
        text="Implement safeguards.",
        act="DPDP",
      )
    ],
    requirements=[
      CatalogRequirement(
        obligation_id="DPDP_SEC_8_SUB_5",
        element_id="technical_measures",
        label="Technical measures",
      )
    ],
  )
  eid = "DPDP_SEC_8_SUB_5::technical_measures"
  node = next(n for n in ir.nodes if n.id == eid)
  assert node.label == "RequirementElement"
  assert any(
    rel.source == "DPDP_SEC_8_SUB_5" and rel.target == eid and rel.type == "HAS_REQUIREMENT"
    for rel in ir.relationships
  )


def test_empty_duties_is_empty_graph() -> None:
  ir = catalog_to_graph_ir([])
  assert ir.nodes == []
  assert ir.relationships == []


def test_kg_export_keeps_catalog_obligation_ids() -> None:
  ir = catalog_to_graph_ir(
    [
      CatalogObligation(
        obligation_id="DPDP_SEC_4_SUB_1",
        title="Notice",
        text="Give notice before processing.",
        act="DPDP",
      ),
      CatalogObligation(
        obligation_id="DPDP_SEC_8",
        title="Safeguards",
        text="Implement safeguards.",
        act="DPDP",
      ),
    ]
  )
  payload = graph_ir_to_kg_dict(ir, law_code="DPDP")
  ids = {row["obligation_id"] for row in payload["obligations"]}
  assert ids == {"DPDP_SEC_4_SUB_1", "DPDP_SEC_8"}
  assert all(row["text"] for row in payload["obligations"])
