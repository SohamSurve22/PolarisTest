"""DOCX document parser."""

from collections.abc import Iterator
from io import BytesIO
from zipfile import BadZipFile

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from document_pipeline.core.exceptions import CorruptedDocumentError
from document_pipeline.parsers.base import BaseParser, ParseResult


class DocxParser(BaseParser):
  """Extracts raw text and metadata from DOCX files."""

  def parse(self, data: bytes, *, encoding: str = "utf-8") -> ParseResult:
    del encoding

    if not data:
      raise CorruptedDocumentError("DOCX file is empty")

    try:
      document = Document(BytesIO(data))
    except BadZipFile as exc:
      raise CorruptedDocumentError("DOCX file is corrupted or unreadable") from exc
    except (KeyError, ValueError) as exc:
      raise CorruptedDocumentError("DOCX file is corrupted or unreadable") from exc

    blocks: list[str] = []
    for block in _iter_block_items(document):
      if isinstance(block, Paragraph):
        blocks.append(block.text)
      elif isinstance(block, Table):
        blocks.append(_table_text(block))

    properties = document.core_properties
    title = _optional_str(properties.title)
    author = _optional_str(properties.author)
    creation_date = (
      properties.created.isoformat()
      if properties.created is not None
      else None
    )

    return ParseResult(
      raw_text="\n".join(blocks),
      title=title,
      author=author,
      creation_date=creation_date,
    )


def _iter_block_items(parent: DocxDocument | _Cell) -> Iterator[Paragraph | Table]:
  parent_element = parent.element.body if isinstance(parent, DocxDocument) else parent._tc

  for child in parent_element.iterchildren():
    if isinstance(child, CT_P):
      yield Paragraph(child, parent)
    elif isinstance(child, CT_Tbl):
      yield Table(child, parent)


def _table_text(table: Table) -> str:
  rows: list[str] = []
  for row in table.rows:
    rows.append("\t".join(cell.text for cell in row.cells))
  return "\n".join(rows)


def _optional_str(value: str | None) -> str | None:
  if value is None:
    return None

  text = value.strip()
  return text or None
