"""Stage 6: Context Builder — structural relationship construction.

Builds contextual relationships between classified clauses without
performing legal reasoning or semantic interpretation.

Components
----------
- ReferenceDetector: finds textual cross-references in clause text.
- NeighborResolver: determines prev/next/neighbour linkages.
- SectionContextBuilder: computes per-section positioning.
- ContextBuilder: orchestrates the above components.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.context import ContextDocument, ContextualClause, Reference
from document_pipeline.models.semantic import ClassifiedClause, ClassifiedDocument

# ---------------------------------------------------------------------------
# ReferenceDetector
# ---------------------------------------------------------------------------

_REFERENCE_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)section\s+(\d+)", "section"),
    (r"(?i)subsection\s*\((\d+)\)", "subsection"),
    (r"(?i)rule\s+(\d+)", "rule"),
    (r"(?i)article\s+(\d+)", "article"),
    (r"(?i)chapter\s+([IVXLCDM]+)", "chapter"),
    (r"(?i)schedule\s+([IVXLCDM]+)", "schedule"),
    (r"(?i)clause\s+(\d+)", "clause"),
    (r"(?i)regulation\s+(\d+)", "regulation"),
    (r"\b[Tt]his\s+Act\b", "act"),
    (r"\b[Tt]hat\s+Act\b", "act"),
    (r"\b[Tt]he\s+Rules\b", "rules"),
    (r"\b[Tt]he\s+Code\b", "code"),
]


@dataclass
class ReferenceDetector:
  """Detects textual cross-references in clause text using regex patterns.

  A future transformer-based implementation would implement the same
  ``detect`` interface.
  """

  def detect(self, text: str) -> list[Reference]:
    """Return all textual references found in *text*."""
    references: list[Reference] = []
    seen: set[tuple[int, int]] = set()

    for pattern, ref_type in _REFERENCE_PATTERNS:
      for match in re.finditer(pattern, text):
        span = (match.start(), match.end())
        if span not in seen:
          seen.add(span)
          references.append(
            Reference(
              reference_text=match.group(0),
              reference_type=ref_type,
              start=match.start(),
              end=match.end(),
            ),
          )

    references.sort(key=lambda r: r.start)
    return references


# ---------------------------------------------------------------------------
# NeighborResolver
# ---------------------------------------------------------------------------

@dataclass
class NeighborInfo:
  """Structural neighbor data for a single clause."""

  previous_clause_id: str | None = None
  next_clause_id: str | None = None
  neighbor_clause_ids: list[str] = field(default_factory=list)


@dataclass
class NeighborResolver:
  """Resolves prev/next/neighbour relationships among an ordered clause list.

  A future implementation may use section-aware or heading-aware neighbour
  resolution; the ``resolve`` interface remains unchanged.
  """

  def resolve(self, clauses: list[ClassifiedClause]) -> dict[str, NeighborInfo]:
    """Return neighbour info for each clause keyed by ``clause_id``."""
    result: dict[str, NeighborInfo] = {}

    for i, clause in enumerate(clauses):
      prev_id = clauses[i - 1].clause.clause_id if i > 0 else None
      next_id = clauses[i + 1].clause.clause_id if i < len(clauses) - 1 else None

      neighbors: list[str] = []
      if prev_id is not None:
        neighbors.append(prev_id)
      if next_id is not None:
        neighbors.append(next_id)

      result[clause.clause.clause_id] = NeighborInfo(
        previous_clause_id=prev_id,
        next_clause_id=next_id,
        neighbor_clause_ids=neighbors,
      )

    return result


# ---------------------------------------------------------------------------
# SectionContextBuilder
# ---------------------------------------------------------------------------

@dataclass
class SectionPosition:
  """Positional information for a clause inside its parent section."""

  position: int = 0
  is_first: bool = False
  is_last: bool = False


@dataclass
class SectionContextBuilder:
  """Computes per-section positional data for every clause.

  A future implementation may account for nested or overlapping sections;
  the ``build`` interface remains unchanged.
  """

  def build(self, clauses: list[ClassifiedClause]) -> dict[str, SectionPosition]:
    """Return section-position info for each clause keyed by ``clause_id``."""
    sections: dict[str, list[ClassifiedClause]] = defaultdict(list)
    for cl in clauses:
      sections[cl.clause.section_id].append(cl)

    result: dict[str, SectionPosition] = {}
    for section_clauses in sections.values():
      count = len(section_clauses)
      for i, cl in enumerate(section_clauses):
        result[cl.clause.clause_id] = SectionPosition(
          position=i,
          is_first=(i == 0),
          is_last=(i == count - 1),
        )

    return result


# ---------------------------------------------------------------------------
# ContextBuilder
# ---------------------------------------------------------------------------

class ContextBuilder(BaseProcessor[ClassifiedDocument, ContextDocument]):
  """Constructs structural context for every classified clause.

  Internally uses ReferenceDetector, NeighborResolver, and
  SectionContextBuilder.  Each component can be replaced independently
  (e.g. with a transformer-based reference detector) without changing
  this stage or downstream consumers.
  """

  def __init__(
    self,
    reference_detector: ReferenceDetector | None = None,
    neighbor_resolver: NeighborResolver | None = None,
    section_context_builder: SectionContextBuilder | None = None,
  ) -> None:
    self._reference_detector = reference_detector or ReferenceDetector()
    self._neighbor_resolver = neighbor_resolver or NeighborResolver()
    self._section_context_builder = section_context_builder or SectionContextBuilder()

  def process(self, input_data: ClassifiedDocument) -> ContextDocument:
    clauses = input_data.clauses

    neighbor_map = self._neighbor_resolver.resolve(clauses)
    section_map = self._section_context_builder.build(clauses)

    contextual: list[ContextualClause] = []
    for cl in clauses:
      cid = cl.clause.clause_id
      neighbor = neighbor_map[cid]
      section_pos = section_map[cid]

      references = self._reference_detector.detect(cl.clause.clause_text)

      contextual.append(
        ContextualClause(
          classified_clause=cl,
          previous_clause_id=neighbor.previous_clause_id,
          next_clause_id=neighbor.next_clause_id,
          section_position=section_pos.position,
          is_first_in_section=section_pos.is_first,
          is_last_in_section=section_pos.is_last,
          neighbor_clause_ids=neighbor.neighbor_clause_ids,
          detected_references=references,
        ),
      )

    return ContextDocument(
      metadata=input_data.metadata,
      contextual_clauses=contextual,
    )
