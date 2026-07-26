"""Semantic extraction input models for downstream analysis."""

from enum import Enum

from pydantic import BaseModel, Field

from document_pipeline.models.clause import Clause
from document_pipeline.models.metadata import DocumentMetadata


class StructuralRole(str, Enum):
  """Structural role of a clause within its document."""

  HEADING = "HEADING"
  STATEMENT = "STATEMENT"
  LIST_ITEM = "LIST_ITEM"
  UNKNOWN = "UNKNOWN"


class ClassificationResult(BaseModel):
  """Classifier output for a single clause.

  A future transformer classifier would return this same model, keeping
  downstream stages unchanged.
  """

  role: StructuralRole = Field(description="Assigned structural role.")
  confidence: float = Field(
    default=1.0,
    ge=0.0,
    le=1.0,
    description=(
      "Prediction confidence (1.0 = deterministic). "
      "A transformer classifier would provide a calibrated score."
    ),
  )
  classification_reason: list[str] = Field(
    default_factory=list,
    description=(
      "Human-readable labels explaining the classification decision "
      "(e.g. 'short_text', 'matches_section_title')."
    ),
  )


class ClassifiedClause(BaseModel):
  """A parser clause annotated with its structural role."""

  clause: Clause = Field(description="The original parser clause (parser model — do not mutate).")
  role: StructuralRole = Field(description="Assigned structural role.")
  confidence: float = Field(
    default=1.0,
    ge=0.0,
    le=1.0,
    description="Prediction confidence for this classification.",
  )
  classification_reason: list[str] = Field(
    default_factory=list,
    description="Human-readable labels explaining the classification decision.",
  )


class ClassifiedDocument(BaseModel):
  """A SegmentedDocument enriched with structural classifications."""

  metadata: DocumentMetadata = Field(description="Document metadata carried through the pipeline.")
  clauses: list[ClassifiedClause] = Field(
    default_factory=list,
    description="Classified clauses in document order.",
  )


class LLMChunk(BaseModel):
  """A text chunk prepared for downstream semantic extraction."""

  chunk_id: str = Field(description="Stable identifier for this chunk.")
  clause_id: str | None = Field(
    default=None,
    description="Source clause identifier, if chunk originates from a clause.",
  )
  text: str = Field(description="Prepared text payload for semantic extraction.")
  token_estimate: int | None = Field(
    default=None,
    ge=0,
    description="Estimated token count for this chunk.",
  )
  context: dict[str, str] = Field(
    default_factory=dict,
    description="Structured context metadata attached to the chunk.",
  )


class SemanticExtractionInput(BaseModel):
  """Final pipeline artifact ready for semantic extraction and analysis."""

  metadata: DocumentMetadata = Field(description="Document metadata carried through the pipeline.")
  chunks: list[LLMChunk] = Field(
    default_factory=list,
    description="Ordered list of text chunks prepared for semantic extraction.",
  )
