"""Metadata and shared primitives for pipeline data models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from document_pipeline.utils.document_ids import generate_document_id


class DocumentFormat(str, Enum):
  """Supported source document formats."""

  PDF = "pdf"
  DOCX = "docx"
  TXT = "txt"
  HTML = "html"
  UNKNOWN = "unknown"


class Span(BaseModel):
  """Character span within a parent text buffer."""

  start: int = Field(ge=0, description="Inclusive start offset in characters.")
  end: int = Field(ge=0, description="Exclusive end offset in characters.")

  def __len__(self) -> int:
    return self.end - self.start


class DocumentMetadata(BaseModel):
  """Metadata describing an uploaded legal document."""

  document_id: str = Field(
    default_factory=generate_document_id,
    description="Stable internal identifier for the document (e.g. DOC_8f2c91d4).",
  )
  filename: str = Field(description="Original filename as uploaded.")
  format: DocumentFormat = Field(description="Detected or declared file format.")
  title: str | None = Field(default=None, description="Document title if available.")
  uploaded_at: datetime | None = Field(
    default=None,
    description="Timestamp when the document was uploaded.",
  )
  source_path: str | None = Field(
    default=None,
    description="Filesystem or storage path to the source file.",
  )
  extra: dict[str, str] = Field(
    default_factory=dict,
    description="Additional key-value metadata for extensibility.",
  )
