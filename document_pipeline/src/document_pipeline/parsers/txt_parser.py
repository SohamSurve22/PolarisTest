"""Plain-text document parser."""

from document_pipeline.core.exceptions import UnreadableDocumentError
from document_pipeline.parsers.base import BaseParser, ParseResult


class TxtParser(BaseParser):
  """Extracts raw text from UTF-8 or other encoded plain-text files."""

  def parse(self, data: bytes, *, encoding: str = "utf-8") -> ParseResult:
    try:
      raw_text = data.decode(encoding)
    except UnicodeDecodeError as exc:
      msg = f"Failed to decode text document using encoding {encoding!r}"
      raise UnreadableDocumentError(msg) from exc

    return ParseResult(raw_text=raw_text)
