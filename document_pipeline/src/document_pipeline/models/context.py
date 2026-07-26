"""Context models for Stage 2: Context Builder.

All models are plain dataclasses, not Pydantic models, to keep the context
layer decoupled from the serialisation framework.  A downstream knowledge-graph
or retrieval layer can convert them as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from document_pipeline.models.metadata import DocumentMetadata
from document_pipeline.models.semantic import ClassifiedClause


@dataclass
class Reference:
  """A textual reference detected inside a clause.

  This is a lightweight detection only — no resolution or linking is performed.
  A future resolver would set ``resolved=True`` and populate ``resolved_clause_id``
  or ``resolved_section_id``.
  """

  reference_text: str = field(default="")
  reference_type: str = field(default="")
  start: int = field(default=0)
  end: int = field(default=0)
  resolved: bool = field(default=False)
  resolved_clause_id: str | None = field(default=None)
  resolved_section_id: str | None = field(default=None)


@dataclass
class ContextualClause:
  """A clause enriched with its structural context within the document.

  Relationships are purely structural — no legal meaning is inferred.
  """

  classified_clause: ClassifiedClause = field(default=None)  # type: ignore[assignment]
  previous_clause_id: str | None = field(default=None)
  next_clause_id: str | None = field(default=None)
  section_position: int = field(default=0)
  is_first_in_section: bool = field(default=False)
  is_last_in_section: bool = field(default=False)
  neighbor_clause_ids: list[str] = field(default_factory=list)
  detected_references: list[Reference] = field(default_factory=list)


@dataclass
class ContextDocument:
  """Output of the Context Builder stage.

  Contains every clause enriched with structural relationships and
  detected references, ready for downstream graph construction,
  retrieval, or legal reasoning.
  """

  metadata: DocumentMetadata = field(default=None)  # type: ignore[assignment]
  contextual_clauses: list[ContextualClause] = field(default_factory=list)
