"""Assembles clause units into clause models."""

from document_pipeline.clause_segmentation.types import ClauseUnit
from document_pipeline.models.clause import Clause
from document_pipeline.models.metadata import DocumentFormat, Span


class ClauseAssembler:
  """Builds ordered clause models from detected clause units."""

  def assemble(
    self,
    section_id: str,
    section_title: str | None,
    document_id: str,
    document_type: DocumentFormat,
    units: list[ClauseUnit],
  ) -> list[Clause]:
    """Create clauses for a section with per-section hierarchical identifiers."""
    clauses: list[Clause] = []
    next_clause_number = 1

    for unit in units:
      clauses.append(
        Clause(
          clause_id=_format_clause_id(section_id, next_clause_number),
          section_id=section_id,
          section_title=section_title,
          document_id=document_id,
          document_type=document_type,
          clause_text=unit.text,
          span=Span(start=unit.start_char, end=unit.end_char),
          clause_number=unit.clause_number,
        ),
      )
      next_clause_number += 1

    return clauses


def _format_clause_id(section_id: str, sequence_number: int) -> str:
  return f"{section_id}_C{sequence_number:03d}"
