"""Print engine status counts vs gold files. Does not call Neo4j."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from policy_compare.service import default_law_paths

from compliance.benchmark_cases import AMBIGUOUS_TEXTS, FAIL_TEXTS, PARTIAL_TEXTS, PASS_TEXTS
from compliance.service import analyze_document


def _document(texts: list[str], filename: str) -> EntityDocument:
  entity_clauses = []
  for index, text in enumerate(texts, start=1):
    clause = Clause(
      clause_id=f"S{index:03d}_C001",
      section_id=f"S{index:03d}",
      section_title=f"Section {index}",
      document_id="DOC_bench",
      document_type=DocumentFormat.TXT,
      clause_text=text,
      span=Span(start=0, end=len(text)),
    )
    classified = ClassifiedClause(
      clause=clause,
      role=StructuralRole.STATEMENT,
      confidence=1.0,
      classification_reason=[],
    )
    entity_clauses.append(
      EntityClause(contextual_clause=ContextualClause(classified_clause=classified), entities=[])
    )
  return EntityDocument(
    metadata=DocumentMetadata(
      document_id="DOC_bench",
      filename=filename,
      format=DocumentFormat.TXT,
    ),
    entity_clauses=entity_clauses,
  )


def main() -> None:
  root = Path(__file__).resolve().parents[3]
  paths = default_law_paths(root)
  suites = [
    ("PASS", PASS_TEXTS, "privacy_policy_1.txt"),
    ("FAIL", FAIL_TEXTS, "Fail_Policy.txt"),
    ("PARTIAL", PARTIAL_TEXTS, "Partial_Policy.txt"),
    ("AMBIGUOUS", AMBIGUOUS_TEXTS, "ambiguous.txt"),
  ]
  print(f"{'suite':<12} {'covered':>8} {'partial':>8} {'missing':>8} {'n/a':>8} {'violation':>10}")
  for name, texts, filename in suites:
    result = analyze_document(_document(texts, filename), paths, search=lambda _: [])
    counts = Counter(row.status for row in result.obligations)
    print(
      f"{name:<12} {counts['covered']:8d} {counts['partial']:8d} "
      f"{counts['missing']:8d} {counts['not_applicable']:8d} {counts['violation']:10d}"
    )


if __name__ == "__main__":
  main()
