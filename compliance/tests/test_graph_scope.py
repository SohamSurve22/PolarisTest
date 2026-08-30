from pathlib import Path

from compliance.graph_scope import ir_from_paths, penalties_for

FIXTURE = Path(__file__).parent / "fixtures" / "analyze_law.json"


def test_ir_from_paths_yields_obligation_ids_not_governance() -> None:
  ir = ir_from_paths([FIXTURE])
  obligation_ids = {node.id for node in ir.nodes if node.label == "Obligation"}
  assert obligation_ids == {"TINY_CONSENT", "TINY_SECURE"}
  all_ids = {node.id for node in ir.nodes}
  assert "TINY_GOVERNANCE" not in all_ids
  assert "DOC_TINY" not in all_ids


def test_penalizes_edge_from_penalty_to_secure() -> None:
  ir = ir_from_paths([FIXTURE])
  edges = {(rel.source, rel.target) for rel in ir.relationships if rel.type == "PENALIZES"}
  assert ("TINY_PENALTY_SEC", "TINY_SECURE") in edges


def test_penalties_for_walks_penalizes_edges() -> None:
  ir = ir_from_paths([FIXTURE])
  linked = penalties_for(ir, "TINY_SECURE")
  assert linked
  assert any(row.amount_crore == 250 for row in linked)
  assert penalties_for(ir, "TINY_CONSENT") == []
