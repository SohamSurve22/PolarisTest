from graph_builder.catalog_ir import CatalogObligation, catalog_to_graph_ir
from graph_builder.graph_ir import GraphRelationship

from compliance.cypher_export import export_cypher
from compliance.models import MatchedClause, ObligationFinding


def test_export_contains_matched_by_and_obligation_id() -> None:
  ir = catalog_to_graph_ir(
    [
      CatalogObligation(
        obligation_id="TINY_SECURE",
        title="Security safeguards",
        act="TINY",
      )
    ]
  )
  ir.relationships.append(
    GraphRelationship(source="TINY_SECURE", target="S002_C001", type="MATCHED_BY")
  )
  finding = ObligationFinding(
    obligation_id="TINY_SECURE",
    title="Security safeguards",
    act="TINY",
    status="partial",
    evidence_quality="HIGH",
    matched_clauses=[
      MatchedClause(clause_id="S002_C001", section_title="Security", text="We encrypt data."),
    ],
  )
  text = export_cypher(ir, [finding])
  assert "MATCHED_BY" in text
  assert "TINY_SECURE" in text
  assert "analyze_document" not in text.lower() or "bolt" not in text.lower()
