"""Intermediate parser models for the ClauseBuilder stage.

ClauseCandidate and ClauseCandidateDocument are purely structural
parser models.  They are NOT semantic clauses.  They represent
coherent discourse units assembled from document blocks.
"""

from pydantic import BaseModel, Field

from document_pipeline.models.metadata import DocumentMetadata


class ClauseCandidate(BaseModel):
  """A coherent discourse unit assembled from one or more document blocks."""

  candidate_id: str
  section_id: str
  block_ids: list[str] = Field(default_factory=list)
  text: str
  order: int
  metadata: dict[str, object] = Field(default_factory=dict)


class ClauseCandidateDocument(BaseModel):
  """Document-level container for clause candidates."""

  metadata: DocumentMetadata
  candidates: list[ClauseCandidate] = Field(default_factory=list)
