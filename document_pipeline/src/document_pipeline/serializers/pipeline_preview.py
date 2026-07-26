"""Serialization models for development pipeline previews."""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from document_pipeline.models.clause import Clause
from document_pipeline.models.metadata import DocumentMetadata
from document_pipeline.models.section import Section
from document_pipeline.models.semantic import LLMChunk, StructuralRole
from document_pipeline.pipeline.orchestrator import PipelineOutputs


class ClassificationPreview(BaseModel):
  """Structural classification for a single clause."""

  clause_id: str = Field(description="Source clause identifier.")
  role: StructuralRole = Field(description="Assigned structural role.")
  confidence: float = Field(description="Classification confidence score.")
  classification_reason: list[str] = Field(
    default_factory=list,
    description="Human-readable labels explaining the classification.",
  )


class ReferencePreview(BaseModel):
  """A cross-reference detected inside a clause."""

  clause_id: str = Field(description="Clause containing the reference.")
  reference_text: str = Field(description="Matched reference text.")
  reference_type: str = Field(description="Reference category (section, rule, etc.).")
  start: int = Field(description="Start offset within clause text.")
  end: int = Field(description="End offset within clause text.")


class EntityPreview(BaseModel):
  """A legal entity detected inside a clause."""

  clause_id: str = Field(description="Clause containing the entity.")
  entity_id: str = Field(description="Stable entity identifier within the document.")
  entity_text: str = Field(description="Matched entity text.")
  entity_type: str = Field(description="Entity category.")
  start_offset: int = Field(description="Start offset within clause text.")
  end_offset: int = Field(description="End offset within clause text.")
  confidence: float = Field(description="Detection confidence score.")
  detection_method: str = Field(description="Detector that produced this entity.")


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
  classifications: list[ClassificationPreview] = Field(
    default_factory=list,
    description="Structural role assigned to each clause.",
  )
  references: list[ReferencePreview] = Field(
    default_factory=list,
    description="Cross-references detected across all clauses.",
  )
  entities: list[EntityPreview] = Field(
    default_factory=list,
    description="Legal entities detected across all clauses.",
  )
  semantic_chunks: list[LLMChunk] = Field(
    default_factory=list,
    description="LLM-ready chunks prepared from enriched clauses.",
  )


def build_pipeline_preview(outputs: PipelineOutputs) -> PipelinePreviewArtifact:
  """Build a preview artifact from a full pipeline run."""
  classifications = [
    ClassificationPreview(
      clause_id=classified.clause.clause_id,
      role=classified.role,
      confidence=classified.confidence,
      classification_reason=list(classified.classification_reason),
    )
    for classified in outputs.classified.clauses
  ]

  references: list[ReferencePreview] = []
  entities: list[EntityPreview] = []

  for entity_clause in outputs.entity.entity_clauses:
    contextual = entity_clause.contextual_clause
    clause_id = contextual.classified_clause.clause.clause_id

    for reference in contextual.detected_references:
      references.append(
        ReferencePreview(
          clause_id=clause_id,
          reference_text=reference.reference_text,
          reference_type=reference.reference_type,
          start=reference.start,
          end=reference.end,
        ),
      )

    for entity in entity_clause.entities:
      entities.append(
        EntityPreview(
          clause_id=clause_id,
          entity_id=entity.entity_id,
          entity_text=entity.entity_text,
          entity_type=entity.entity_type.value,
          start_offset=entity.start_offset,
          end_offset=entity.end_offset,
          confidence=entity.confidence,
          detection_method=entity.detection_method,
        ),
      )

  return PipelinePreviewArtifact(
    metadata=outputs.semantic.metadata,
    raw_text=outputs.loaded.raw_text,
    page_count=outputs.loaded.page_count,
    extraction_notes=list(outputs.loaded.extraction_notes),
    cleaned_text=outputs.cleaned.cleaned_text,
    cleaning_notes=list(outputs.cleaned.cleaning_notes),
    full_text=outputs.sectioned.full_text,
    sections=outputs.sectioned.sections,
    clauses=outputs.segmented.clauses,
    classifications=classifications,
    references=references,
    entities=entities,
    semantic_chunks=outputs.semantic.chunks,
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
