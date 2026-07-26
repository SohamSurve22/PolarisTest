"""Document-level models for loading and cleaning stages."""

from pydantic import BaseModel, Field

from document_pipeline.models.metadata import DocumentMetadata


class DocumentSource(BaseModel):
  """Reference to a legal document before it enters the pipeline.

  This is the entry-point model — typically created when a file is uploaded
  or referenced for processing.
  """

  metadata: DocumentMetadata = Field(description="Descriptive metadata for the document.")
  encoding: str = Field(default="utf-8", description="Expected text encoding for text-based formats.")


class LoadedDocument(BaseModel):
  """A document whose raw text has been extracted from its source file."""

  metadata: DocumentMetadata = Field(description="Document metadata carried through the pipeline.")
  raw_text: str = Field(description="Unprocessed text extracted from the source document.")
  page_count: int | None = Field(
    default=None,
    ge=0,
    description="Number of pages if applicable (e.g. PDF).",
  )
  extraction_notes: list[str] = Field(
    default_factory=list,
    description="Non-fatal notes recorded during extraction.",
  )


class CleanedDocument(BaseModel):
  """A document whose text has been normalized and cleaned for analysis."""

  metadata: DocumentMetadata = Field(description="Document metadata carried through the pipeline.")
  cleaned_text: str = Field(description="Normalized text ready for structural analysis.")
  cleaning_notes: list[str] = Field(
    default_factory=list,
    description="Notes about transformations applied during cleaning.",
  )
