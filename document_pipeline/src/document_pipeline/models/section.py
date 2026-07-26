"""Section-level models for the section extraction stage."""

from pydantic import BaseModel, Field

from document_pipeline.models.metadata import DocumentMetadata, Span


class Section(BaseModel):
  """A detected structural section within a legal document."""

  section_id: str = Field(description="Stable identifier for this section.")
  title: str | None = Field(default=None, description="Detected section heading, if any.")
  text: str = Field(description="Full text content of the section.")
  span: Span = Field(description="Character span of this section in the cleaned document.")
  level: int = Field(default=1, ge=1, description="Hierarchical depth of the section.")
  parent_section_id: str | None = Field(
    default=None,
    description="Identifier of the parent section, if nested.",
  )


class SectionedDocument(BaseModel):
  """A document partitioned into structural sections."""

  metadata: DocumentMetadata = Field(description="Document metadata carried through the pipeline.")
  full_text: str = Field(description="Complete cleaned text for reference.")
  sections: list[Section] = Field(
    default_factory=list,
    description="Ordered list of detected sections.",
  )
