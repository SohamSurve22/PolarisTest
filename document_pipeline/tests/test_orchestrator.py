"""Integration tests for the document pipeline orchestrator."""

from pathlib import Path

from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.orchestrator import create_default_orchestrator
from document_pipeline.serializers.pipeline_preview import build_pipeline_preview


def _source_for_text(text: str, tmp_path: Path) -> DocumentSource:
  file_path = tmp_path / "policy.txt"
  file_path.write_text(text, encoding="utf-8")

  metadata = DocumentMetadata(
    document_id="DOC_test",
    filename="policy.txt",
    format=DocumentFormat.TXT,
    source_path=str(file_path),
  )
  return DocumentSource(metadata=metadata)


def test_orchestrator_runs_all_stages(tmp_path: Path) -> None:
  file_path = tmp_path / "policy.txt"
  file_path.write_text(
    "Section 4\n\nThe Data Fiduciary shall process personal data within 30 days.\n",
    encoding="utf-8",
  )

  metadata = DocumentMetadata(
    document_id="DOC_test",
    filename="policy.txt",
    format=DocumentFormat.TXT,
    source_path=str(file_path),
  )
  source = DocumentSource(metadata=metadata)
  orchestrator = create_default_orchestrator()

  outputs = orchestrator.run(source)

  assert outputs.loaded.raw_text
  assert outputs.cleaned.cleaned_text
  assert outputs.sectioned.sections
  assert outputs.segmented.clauses
  assert outputs.classified.clauses
  assert outputs.context.contextual_clauses
  assert outputs.entity.entity_clauses
  assert outputs.semantic.chunks
  assert len(outputs.semantic.chunks) == len(outputs.segmented.clauses)


def test_orchestrator_detects_entities_and_references(tmp_path: Path) -> None:
  source = _source_for_text(
    "Section 3\n\n"
    "As required under Section 4, the Data Fiduciary shall process personal "
    "data within 30 days.\n\n"
    "Section 4\n\n"
    "Personal data shall not be retained beyond the period stated above.\n",
    tmp_path,
  )

  orchestrator = create_default_orchestrator()
  outputs = orchestrator.run(source)

  entity_texts = {
    entity.entity_text
    for entity_clause in outputs.entity.entity_clauses
    for entity in entity_clause.entities
  }
  assert "Data Fiduciary" in entity_texts
  assert "personal data" in entity_texts

  reference_texts = {
    reference.reference_text
    for contextual in outputs.context.contextual_clauses
    for reference in contextual.detected_references
  }
  assert any("Section 4" in text for text in reference_texts)


def test_build_pipeline_preview_includes_enriched_fields(tmp_path: Path) -> None:
  source = _source_for_text(
    "Section 3\n\n"
    "As required under Section 4, the Data Fiduciary shall process personal "
    "data within 30 days.\n\n"
    "Section 4\n\n"
    "Personal data shall not be retained beyond the period stated above.\n",
    tmp_path,
  )
  outputs = create_default_orchestrator().run(source)
  artifact = build_pipeline_preview(outputs)

  assert artifact.classifications
  assert artifact.references
  assert artifact.entities
  assert artifact.semantic_chunks
  assert artifact.classifications[0].role.value in {
    "HEADING",
    "STATEMENT",
    "LIST_ITEM",
    "UNKNOWN",
  }
