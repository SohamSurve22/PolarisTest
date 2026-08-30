from pathlib import Path

import pytest
from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from vectorization.models import SearchHit

from compliance.service import AnalyzeError, analyze_document

FIXTURE = Path(__file__).parent / "fixtures" / "analyze_law.json"


def _clause(text: str, *, clause_id: str = "S002_C001") -> Clause:
  return Clause(
    clause_id=clause_id,
    section_id="S002",
    section_title="Consent",
    document_id="DOC_x",
    document_type=DocumentFormat.TXT,
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )


def _document(*clauses: Clause) -> EntityDocument:
  entity_clauses = []
  for clause in clauses:
    classified = ClassifiedClause(
      clause=clause,
      role=StructuralRole.STATEMENT,
      confidence=1.0,
      classification_reason=[],
    )
    entity_clauses.append(
      EntityClause(
        contextual_clause=ContextualClause(classified_clause=classified),
        entities=[],
      )
    )
  return EntityDocument(
    metadata=DocumentMetadata(
      document_id="DOC_x",
      filename="policy.txt",
      format=DocumentFormat.TXT,
    ),
    entity_clauses=entity_clauses,
  )


def _hit(obligation_id: str, score: float) -> SearchHit:
  return SearchHit(
    score=score,
    source_type="kg_obligation",
    payload={"obligation_id": obligation_id, "law_code": "TINY"},
  )


def test_covered_and_missing_with_penalty() -> None:
  def search(query: str) -> list[SearchHit]:
    if "consent" in query.lower():
      return [_hit("TINY_CONSENT", 0.8)]
    return []

  result = analyze_document(_document(_clause("We obtain consent from users.")), [FIXTURE], search=search)
  by_id = {row.obligation_id: row for row in result.obligations}
  assert by_id["TINY_CONSENT"].status == "covered"
  assert by_id["TINY_SECURE"].status == "missing"
  assert any(gap.obligation_id == "TINY_SECURE" for gap in result.gaps)
  assert not any(gap.obligation_id == "TINY_CONSENT" for gap in result.gaps)
  assert any(pen.obligation_id == "TINY_SECURE" and pen.amount_crore == 250 for pen in result.penalties)
  assert all(pen.eligibility == "potential_exposure" for pen in result.penalties)
  assert all(pen.not_a_determination_of_liability for pen in result.penalties)
  assert not any(pen.obligation_id == "TINY_CONSENT" for pen in result.penalties)
  assert result.applicable_laws == ["TINY"]
  assert result.jurisdiction == "IN"
  assert result.document_id == "DOC_x"
  assert result.source_filename == "policy.txt"
  assert by_id["TINY_CONSENT"].matched_clauses
  assert "consent" in by_id["TINY_CONSENT"].matched_clauses[0].text.lower()


def test_partial_score() -> None:
  def search(_query: str) -> list[SearchHit]:
    return [_hit("TINY_CONSENT", 0.4)]

  result = analyze_document(_document(_clause("consent mentioned")), [FIXTURE], search=search)
  consent = next(row for row in result.obligations if row.obligation_id == "TINY_CONSENT")
  assert consent.status == "partial"
  assert any(gap.obligation_id == "TINY_CONSENT" for gap in result.gaps)


def test_clause_credits_multiple_duties() -> None:
  def search(_query: str) -> list[SearchHit]:
    return [_hit("TINY_CONSENT", 0.81), _hit("TINY_SECURE", 0.78)]

  result = analyze_document(_document(_clause("We obtain consent from users.")), [FIXTURE], search=search)
  by_id = {row.obligation_id: row for row in result.obligations}
  assert by_id["TINY_CONSENT"].status == "covered"
  assert by_id["TINY_SECURE"].matched_clauses or by_id["TINY_SECURE"].status != "covered"


def test_high_vector_score_without_title_overlap_is_partial() -> None:
  def search(_query: str) -> list[SearchHit]:
    return [_hit("TINY_SECURE", 0.88)]

  result = analyze_document(_document(_clause("We obtain consent from users.")), [FIXTURE], search=search)
  secure = next(row for row in result.obligations if row.obligation_id == "TINY_SECURE")
  assert secure.status == "partial"
  assert any(gap.obligation_id == "TINY_SECURE" for gap in result.gaps)


def test_unknown_qdrant_id_is_not_an_obligation() -> None:
  def search(_query: str) -> list[SearchHit]:
    return [_hit("NOT_IN_GRAPH", 0.99), _hit("TINY_CONSENT", 0.8)]

  result = analyze_document(
    _document(_clause("We obtain consent from users.")),
    [FIXTURE],
    search=search,
  )
  ids = {row.obligation_id for row in result.obligations}
  assert "NOT_IN_GRAPH" not in ids
  assert "TINY_CONSENT" in ids


def test_duty_set_comes_from_graph_ir(monkeypatch: object) -> None:
  from graph_builder.catalog_ir import CatalogObligation, catalog_to_graph_ir

  slim = catalog_to_graph_ir(
    [
      CatalogObligation(
        obligation_id="TINY_CONSENT",
        title="Consent required",
        act="TINY",
        summary="Must get consent.",
      ),
    ]
  )
  monkeypatch.setattr("compliance.service.ir_from_paths", lambda _paths: slim)

  def search(_query: str) -> list[SearchHit]:
    return [_hit("TINY_SECURE", 0.99)]

  result = analyze_document(
    _document(_clause("We obtain consent from users.")),
    [FIXTURE],
    search=search,
  )
  ids = {row.obligation_id for row in result.obligations}
  assert ids == {"TINY_CONSENT"}
  assert "TINY_SECURE" not in ids


def test_empty_catalog(tmp_path: Path) -> None:
  empty = tmp_path / "empty.json"
  empty.write_text("[]", encoding="utf-8")
  result = analyze_document(_document(_clause("anything")), [empty], search=lambda _: [])
  assert result.obligations == []
  assert result.gaps == []
  assert result.penalties == []


def test_unsupported_jurisdiction() -> None:
  with pytest.raises(ValueError, match="Unsupported jurisdiction"):
    analyze_document(_document(_clause("x")), [FIXTURE], jurisdiction="US", search=lambda _: [])


def test_search_failure_is_analyze_error() -> None:
  def search(_query: str) -> list[SearchHit]:
    raise ConnectionError("qdrant down")

  with pytest.raises(AnalyzeError, match="qdrant down"):
    analyze_document(_document(_clause("consent")), [FIXTURE], search=search)


def test_default_search_keeps_partial_hits(monkeypatch: object) -> None:
  captured: dict[str, object] = {}

  def fake_search_text(query: str, **kwargs: object) -> list[SearchHit]:
    captured["query"] = query
    captured["source_type"] = kwargs.get("source_type")
    captured["min_score"] = kwargs.get("min_score")
    return []

  monkeypatch.setattr("vectorization.pipeline.search_text", fake_search_text)
  from compliance.service import default_search

  default_search("consent clause")
  assert captured["query"] == "consent clause"
  assert captured["source_type"] == "kg_obligation"
  assert captured["min_score"] == 0.30
