from pathlib import Path

from compliance.catalog import load_catalog

FIXTURE = Path(__file__).parent / "fixtures" / "analyze_law.json"


def test_catalog_keeps_duties_and_drops_governance() -> None:
  catalog = load_catalog([FIXTURE])
  ids = {chunk.doc_id for chunk in catalog.obligations}
  assert ids == {"TINY_CONSENT", "TINY_SECURE"}


def test_catalog_links_penalty_to_obligation() -> None:
  catalog = load_catalog([FIXTURE])
  linked = catalog.penalties_for("TINY_SECURE")
  assert linked
  assert any(row.amount_crore == 250 for row in linked)
  assert catalog.penalties_for("TINY_CONSENT") == []


def test_empty_paths_yield_empty_catalog(tmp_path: Path) -> None:
  empty = tmp_path / "empty.json"
  empty.write_text("[]", encoding="utf-8")
  catalog = load_catalog([empty])
  assert catalog.obligations == []
  assert catalog.penalties == []
