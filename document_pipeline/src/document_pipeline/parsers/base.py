"""Abstract base for format-specific document parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParseResult:
  """Raw extraction output produced by a format-specific parser."""

  raw_text: str
  page_count: int | None = None
  title: str | None = None
  author: str | None = None
  creation_date: str | None = None
  extraction_notes: list[str] = field(default_factory=list)


class BaseParser(ABC):
  """Strategy interface for extracting raw text from a document format."""

  @abstractmethod
  def parse(self, data: bytes, *, encoding: str = "utf-8") -> ParseResult:
    """Extract raw text and available metadata from document bytes.

    Args:
      data: Raw file contents.
      encoding: Text encoding for text-based formats.

    Returns:
      Parsed content without cleaning or normalization.

    Raises:
      CorruptedDocumentError: If the bytes are not a valid document of this format.
      UnreadableDocumentError: If the bytes cannot be decoded or interpreted.
    """
