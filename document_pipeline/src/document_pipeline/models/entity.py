"""Entity models for Stage 3: Legal Entity Extraction.

All models are plain dataclasses.  A downstream knowledge-graph or
retrieval layer can convert them as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from document_pipeline.models.context import ContextualClause
from document_pipeline.models.metadata import DocumentMetadata


class EntityType(str, Enum):
  """Types of legal entities that can be detected in clause text."""

  LEGAL_ACTOR = "LEGAL_ACTOR"
  PERSON = "PERSON"
  ORGANIZATION = "ORGANIZATION"
  LEGAL_DOCUMENT = "LEGAL_DOCUMENT"
  LEGAL_OBJECT = "LEGAL_OBJECT"
  TIME = "TIME"
  DATE = "DATE"
  LAW_REFERENCE = "LAW_REFERENCE"


@dataclass
class Entity:
  """A single detected entity within a clause."""

  entity_id: str = field(default="")
  entity_text: str = field(default="")
  entity_type: EntityType = field(default=EntityType.LEGAL_ACTOR)
  start_offset: int = field(default=0)
  end_offset: int = field(default=0)
  confidence: float = field(default=1.0)
  detection_method: str = field(default="")


@dataclass
class EntityClause:
  """A contextual clause annotated with its detected entities."""

  contextual_clause: ContextualClause = field(default=None)  # type: ignore[assignment]
  entities: list[Entity] = field(default_factory=list)


@dataclass
class EntityDocument:
  """Output of the Entity Extractor stage."""

  metadata: DocumentMetadata = field(default=None)  # type: ignore[assignment]
  entity_clauses: list[EntityClause] = field(default_factory=list)
