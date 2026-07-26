"""Serialization models for development pipeline previews."""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from document_pipeline.models.clause import Clause
from document_pipeline.models.metadata import DocumentMetadata
from document_pipeline.models.section import Section


class PipelinePreviewArtifact(BaseModel):
  """Development artifact combining outputs from implemented pipeline stages."""

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
  cleaned_text: str = Field(description="Normalized text ready for structural analysis.")
  cleaning_notes: list[str] = Field(
    default_factory=list,
    description="Notes about transformations applied during cleaning.",
  )
  full_text: str = Field(description="Complete cleaned text used for section extraction.")
  sections: list[Section] = Field(
    default_factory=list,
    description="Ordered list of detected sections.",
  )
  clauses: list[Clause] = Field(
    default_factory=list,
    description="All clauses extracted across sections.",
  )


def serialize_pipeline_preview(artifact: PipelinePreviewArtifact) -> str:
  """Serialize a pipeline preview artifact to indented JSON."""
  return json.dumps(
    artifact.model_dump(mode="json"),
    indent=2,
    ensure_ascii=False,
  ) + "\n"


def save_pipeline_preview(artifact: PipelinePreviewArtifact, output_dir: str | Path) -> Path:
  """Serialize and write the preview artifact to ``{output_dir}/{document_id}.json``."""
  path = Path(output_dir).expanduser().resolve()
  path.mkdir(parents=True, exist_ok=True)

  filename = f"{artifact.metadata.document_id}.json"
  dest = path / filename
  dest.write_text(serialize_pipeline_preview(artifact), encoding="utf-8")
  return dest
