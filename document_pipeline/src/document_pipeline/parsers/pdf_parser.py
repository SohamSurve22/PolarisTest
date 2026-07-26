"""PDF document parser."""

from io import BytesIO
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from document_pipeline.core.exceptions import CorruptedDocumentError
from document_pipeline.parsers.base import BaseParser, ParseResult


class PdfParser(BaseParser):
  """Extracts raw text and metadata from PDF files without OCR."""

  def parse(self, data: bytes, *, encoding: str = "utf-8") -> ParseResult:
    del encoding

    if not data:
      raise CorruptedDocumentError("PDF file is empty")

    try:
      reader = PdfReader(BytesIO(data), strict=True)
    except PdfReadError as exc:
      raise CorruptedDocumentError("PDF file is corrupted or unreadable") from exc

    page_texts: list[str] = []
    for page in reader.pages:
      extracted = page.extract_text()
      if extracted is not None:
        page_texts.append(extracted)

    metadata = reader.metadata
    title = _metadata_value(metadata, "/Title")
    author = _metadata_value(metadata, "/Author")
    creation_date = _metadata_value(metadata, "/CreationDate")

    return ParseResult(
      raw_text="".join(page_texts),
      page_count=len(reader.pages),
      title=title,
      author=author,
      creation_date=creation_date,
    )


def _metadata_value(metadata: object | None, key: str) -> str | None:
  if metadata is None:
    return None

  getter = getattr(metadata, "get", None)
  if getter is None:
    return None

  value: Any = getter(key)
  if value is None:
    return None

  text = str(value).strip()
  return text or None
