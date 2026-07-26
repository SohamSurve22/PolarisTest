"""Clause-level models for the clause extraction stage."""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span


class Clause(BaseModel):
  """A discrete legal clause extracted from a section."""

  model_config = ConfigDict(populate_by_name=True)

  clause_id: str = Field(description="Stable hierarchical identifier for this clause.")
  section_id: str = Field(description="Identifier of the parent section.")
  section_title: str | None = Field(
    default=None,
    description="Title of the parent section, if any.",
  )
  document_id: str = Field(description="Stable internal identifier of the source document.")
  document_type: DocumentFormat = Field(
    description="Format/type of the source document.",
  )
  clause_text: str = Field(
    validation_alias=AliasChoices("clause_text", "text"),
    description="Full text of the clause.",
  )
  span: Span = Field(description="Character span of this clause within the section text.")
  clause_number: str | None = Field(
    default=None,
    description="Detected clause numbering label (e.g. '3.1(a)').",
  )

  @property
  def text(self) -> str:
    """Backward-compatible alias for :attr:`clause_text`."""
    return self.clause_text


class SegmentedDocument(BaseModel):
  """A document whose sections have been decomposed into clauses."""

  metadata: DocumentMetadata = Field(description="Document metadata carried through the pipeline.")
  clauses: list[Clause] = Field(
    default_factory=list,
    description="All clauses extracted across sections.",
  )
