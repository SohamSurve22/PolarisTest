"""Development preview command for the document pipeline."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "output"

from document_pipeline.core.exceptions import DocumentPipelineError
from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.block_extractor import DocumentBlockExtractor
from document_pipeline.pipeline.stages.clause_builder import ClauseBuilder
from document_pipeline.pipeline.stages.clause_extractor import ClauseExtractor
from document_pipeline.pipeline.stages.cleaner import DocumentCleaner
from document_pipeline.pipeline.stages.loader import DocumentLoader
from document_pipeline.pipeline.stages.section_extractor import SectionExtractor
from document_pipeline.serializers.pipeline_preview import (
  PipelinePreviewArtifact,
  save_pipeline_preview,
  serialize_pipeline_preview,
)
from document_pipeline.utils.document_ids import generate_document_id

_SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def register_preview_command(
  subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
  """Register the preview subcommand."""
  preview_parser = subparsers.add_parser(
    "preview",
    help="Run implemented pipeline stages and print a JSON preview artifact.",
  )
  preview_parser.add_argument(
    "path",
    nargs="?",
    help="Path to a .txt, .pdf, or .docx document.",
  )
  preview_parser.add_argument(
    "--text",
    help="Inline plain-text document content to preview.",
  )
  preview_parser.add_argument(
    "--output",
    help="Optional path to write the JSON artifact.",
  )
  preview_parser.set_defaults(handler=_handle_preview)


def _handle_preview(args: argparse.Namespace) -> int:
  if args.text and args.path:
    print("error: provide either a file path or --text, not both.", file=sys.stderr)
    return 2

  if not args.text and not args.path:
    print("error: provide a file path or --text.", file=sys.stderr)
    return 2

  try:
    if args.text is not None:
      artifact = _run_preview_from_text(args.text)
    else:
      artifact = _run_preview_from_path(Path(args.path))
  except DocumentPipelineError as exc:
    print(f"error: {exc}", file=sys.stderr)
    return 1
  except OSError as exc:
    print(f"error: {exc}", file=sys.stderr)
    return 1

  payload = serialize_pipeline_preview(artifact)

  if args.output:
    output_path = Path(args.output)
    output_path.write_text(payload, encoding="utf-8")
  else:
    sys.stdout.write(payload)

  saved = save_pipeline_preview(artifact, _OUTPUT_DIR)
  print(f"Preview saved to {saved}", file=sys.stderr)

  return 0


def _run_preview_from_path(path: Path) -> PipelinePreviewArtifact:
  resolved = path.expanduser().resolve()
  if not resolved.is_file():
    msg = f"Document not found: {resolved}"
    raise OSError(msg)

  extension = resolved.suffix.lower()
  if extension not in _SUPPORTED_EXTENSIONS:
    msg = f"Unsupported file type: {extension or 'unknown'}"
    raise OSError(msg)

  source = _build_source(resolved)
  return _run_pipeline(source)


def _run_preview_from_text(text: str) -> PipelinePreviewArtifact:
  with tempfile.NamedTemporaryFile(
    mode="w",
    encoding="utf-8",
    suffix=".txt",
    delete=False,
  ) as handle:
    handle.write(text)
    temp_path = Path(handle.name)

  try:
    source = _build_source(temp_path)
    return _run_pipeline(source)
  finally:
    temp_path.unlink(missing_ok=True)


def _build_source(path: Path) -> DocumentSource:
  document_format = _format_from_extension(path.suffix)
  metadata = DocumentMetadata(
    document_id=generate_document_id(),
    filename=path.name,
    format=document_format,
    source_path=str(path),
  )
  return DocumentSource(metadata=metadata)


def _format_from_extension(extension: str) -> DocumentFormat:
  mapping = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".txt": DocumentFormat.TXT,
  }
  return mapping.get(extension.lower(), DocumentFormat.UNKNOWN)


def _run_pipeline(source: DocumentSource) -> PipelinePreviewArtifact:
  loader = DocumentLoader()
  cleaner = DocumentCleaner()
  section_extractor = SectionExtractor()
  block_extractor = DocumentBlockExtractor()
  clause_builder = ClauseBuilder()
  clause_extractor = ClauseExtractor()

  loaded = loader.process(source)
  cleaned = cleaner.process(loaded)
  sectioned = section_extractor.process(cleaned)
  blocked = block_extractor.process(sectioned)
  candidate_doc = clause_builder.process(blocked)
  segmented = clause_extractor.process(candidate_doc)

  return PipelinePreviewArtifact(
    metadata=segmented.metadata,
    raw_text=loaded.raw_text,
    page_count=loaded.page_count,
    extraction_notes=list(loaded.extraction_notes),
    cleaned_text=cleaned.cleaned_text,
    cleaning_notes=list(cleaned.cleaning_notes),
    full_text=sectioned.full_text,
    sections=sectioned.sections,
    clauses=segmented.clauses,
  )
