"""Stage 6: Clause Extraction — converts clause candidates into legal clauses.

This stage consumes ClauseCandidateDocument (output of ClauseBuilder)
and produces SegmentedDocument.  Each candidate's text is split into
sentences and assigned clause IDs with per-section numbering.
"""

from __future__ import annotations

from collections import defaultdict

from document_pipeline.clause_segmentation.clause_assembler import ClauseAssembler
from document_pipeline.clause_segmentation.sentence_splitter import SentenceSplitter
from document_pipeline.clause_segmentation.types import ClauseUnit
from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.candidate import ClauseCandidate, ClauseCandidateDocument
from document_pipeline.models.clause import Clause, SegmentedDocument


class ClauseExtractor(BaseProcessor[ClauseCandidateDocument, SegmentedDocument]):
  """Converts clause candidates into ordered legal clauses.

  Splits each candidate's text into sentences, collects them per
  section, then assigns hierarchical clause IDs (S001_C001 etc.)
  and produces a SegmentedDocument.
  """

  def __init__(
    self,
    sentence_splitter: SentenceSplitter | None = None,
    clause_assembler: ClauseAssembler | None = None,
  ) -> None:
    self._sentence_splitter = sentence_splitter or SentenceSplitter()
    self._clause_assembler = clause_assembler or ClauseAssembler()

  def process(self, input_data: ClauseCandidateDocument) -> SegmentedDocument:
    section_units: dict[str, list[ClauseUnit]] = defaultdict(list)
    section_titles: dict[str, str | None] = {}

    for candidate in input_data.candidates:
      section_title = _get_section_title(candidate)
      section_titles.setdefault(candidate.section_id, section_title)
      units = self._sentence_splitter.split(candidate.text)
      section_units[candidate.section_id].extend(units)

    clauses: list[Clause] = []
    document_id = input_data.metadata.document_id
    document_type = input_data.metadata.format

    for section_id, units in section_units.items():
      section_clauses = self._clause_assembler.assemble(
        section_id=section_id,
        section_title=section_titles.get(section_id),
        document_id=document_id,
        document_type=document_type,
        units=units,
      )
      clauses.extend(section_clauses)

    return SegmentedDocument(
      metadata=input_data.metadata,
      clauses=clauses,
    )


def _get_section_title(candidate: ClauseCandidate) -> str | None:
  """Extract section_title from candidate metadata."""
  raw = candidate.metadata.get("section_title")
  if isinstance(raw, str) and raw:
    return raw
  return None
