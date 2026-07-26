"""Stage 1: Document Loading."""

from pathlib import Path

from document_pipeline.core.base import BaseProcessor
from document_pipeline.core.exceptions import (
  CorruptedDocumentError,
  UnreadableDocumentError,
  UnsupportedFileTypeError,
)
from document_pipeline.models.document import DocumentSource, LoadedDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.parsers.base import BaseParser, ParseResult
from document_pipeline.parsers.docx_parser import DocxParser
from document_pipeline.parsers.pdf_parser import PdfParser
from document_pipeline.parsers.txt_parser import TxtParser

_EXTENSION_TO_FORMAT: dict[str, DocumentFormat] = {
  ".pdf": DocumentFormat.PDF,
  ".docx": DocumentFormat.DOCX,
  ".txt": DocumentFormat.TXT,
}


class DocumentLoader(BaseProcessor[DocumentSource, LoadedDocument]):
  """Extracts raw text and metadata from a source legal document.

  Format-specific parsing is delegated to strategy parsers selected by
  file extension. No cleaning, normalization, or structural analysis is
  performed at this stage.
  """

  def __init__(self, parsers: dict[DocumentFormat, BaseParser] | None = None) -> None:
    self._parsers: dict[DocumentFormat, BaseParser] = parsers or {
      DocumentFormat.PDF: PdfParser(),
      DocumentFormat.DOCX: DocxParser(),
      DocumentFormat.TXT: TxtParser(),
    }

  def process(self, input_data: DocumentSource) -> LoadedDocument:
    """Load a document from its source reference."""
    source_path = input_data.metadata.source_path or input_data.metadata.filename
    file_path = Path(source_path)
    document_format = _detect_format(file_path)

    parser = self._parsers.get(document_format)
    if parser is None:
      msg = f"Unsupported file type: {file_path.suffix.lower() or 'unknown'}"
      raise UnsupportedFileTypeError(msg)

    try:
      data = file_path.read_bytes()
    except FileNotFoundError as exc:
      msg = f"Document not found: {file_path}"
      raise UnreadableDocumentError(msg) from exc
    except OSError as exc:
      msg = f"Unable to read document: {file_path}"
      raise UnreadableDocumentError(msg) from exc

    try:
      result = parser.parse(data, encoding=input_data.encoding)
    except (CorruptedDocumentError, UnreadableDocumentError):
      raise
    except Exception as exc:
      msg = f"Failed to parse document: {file_path.name}"
      raise CorruptedDocumentError(msg) from exc

    metadata = _build_metadata(input_data.metadata, document_format, result)

    return LoadedDocument(
      metadata=metadata,
      raw_text=result.raw_text,
      page_count=result.page_count,
      extraction_notes=list(result.extraction_notes),
    )


def _detect_format(file_path: Path) -> DocumentFormat:
  extension = file_path.suffix.lower()
  return _EXTENSION_TO_FORMAT.get(extension, DocumentFormat.UNKNOWN)


def _build_metadata(
  source_metadata: DocumentMetadata,
  document_format: DocumentFormat,
  result: ParseResult,
) -> DocumentMetadata:
  extra = dict(source_metadata.extra)
  if result.author is not None:
    extra.setdefault("author", result.author)
  if result.creation_date is not None:
    extra.setdefault("creation_date", result.creation_date)

  title = source_metadata.title or result.title

  return source_metadata.model_copy(
    update={
      "format": document_format,
      "title": title,
      "extra": extra,
    },
  )
