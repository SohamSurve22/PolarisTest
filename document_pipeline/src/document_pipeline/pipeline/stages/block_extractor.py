"""Stage 4: Document Block Extraction — preserves document layout.

This stage sits between SectionExtractor and ClauseExtractor.
It classifies section content into structural blocks (headings,
paragraphs, lists, tables, etc.) without inferring legal semantics.
"""

from __future__ import annotations

import re

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.block import BlockDocument, BlockType, DocumentBlock
from document_pipeline.models.section import Section, SectionedDocument

_BULLET_RE = re.compile(r"^\s*[-*•]\s+")
_NUMBERED_RE = re.compile(
  r"^\s*(?:\d+(?:\.\d+)*[.)]|\(\d+\)|[A-Za-z][.)]|\([A-Za-z]\))\s+",
)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
_NOTE_RE = re.compile(r"^\s*Note[:\s]|^NOTE[:\s]")
_QUOTE_RE = re.compile(r"^\s*>\s+")
_HEADING_LIKE_RE = re.compile(
  r"^(?P<title>[A-Z][A-Za-z0-9'&()/\-]+(?:\s+[A-Z][A-Za-z0-9'&()/\-]+){0,8})\s*$",
)

_MAX_IMPLICIT_LIST_WORDS = 5
_MAX_HEADING_WORDS = 10


class DocumentBlockExtractor(BaseProcessor[SectionedDocument, BlockDocument]):
  """Classifies document content into structural blocks.

  This stage is purely structural — it NEVER infers legal semantics.
  It preserves original document layout so downstream stages receive
  well-classified content.
  """

  def process(self, input_data: SectionedDocument) -> BlockDocument:
    blocks: list[DocumentBlock] = []
    next_order = 1

    for section in input_data.sections:
      section_blocks, next_order = self._extract_section_blocks(
        section=section,
        section_title=section.title,
        start_order=next_order,
      )
      blocks.extend(section_blocks)

    return BlockDocument(metadata=input_data.metadata, blocks=blocks)

  def _extract_section_blocks(
    self,
    section: Section,
    section_title: str | None,
    start_order: int,
  ) -> tuple[list[DocumentBlock], int]:
    lines = _iter_line_entries(section.text)
    blocks: list[DocumentBlock] = []
    next_block_num = 1
    order = start_order
    i = 0

    # If the section has a title, the first non-empty line is the heading.
    if section_title and lines:
      first_offset, first_line = lines[0]
      stripped = first_line.strip()
      if stripped and _line_matches_heading(stripped, section_title):
        block_id = _format_block_id(section.section_id, next_block_num)
        next_block_num += 1
        blocks.append(
          DocumentBlock(
            block_id=block_id,
            section_id=section.section_id,
            type=BlockType.HEADING,
            text=stripped,
            level=section.level,
            order=order,
            metadata={
              "section_title": section_title,
              "section_start_char": first_offset,
              "section_end_char": first_offset + len(first_line),
            },
          ),
        )
        order += 1
        i += 1

    # Process remaining lines
    while i < len(lines):
      offset, line = lines[i]
      stripped = line.strip()

      if not stripped:
        i += 1
        continue

      # --- Explicit list items (bullet / numbered) ---
      marker = _extract_list_marker(stripped)
      if marker is not None:
        list_items, i = _collect_list_items(lines, i, section, next_block_num)
        block_id = _format_block_id(section.section_id, next_block_num)
        next_block_num += 1
        list_block = DocumentBlock(
          block_id=block_id,
          section_id=section.section_id,
          type=BlockType.LIST,
          text="",
          order=order,
          metadata={"section_title": section_title},
          children=list_items,
        )
        for child in list_items:
          child.parent_block_id = block_id
        blocks.append(list_block)
        order += 1
        continue

      # --- Table row ---
      if _TABLE_RE.match(stripped):
        table_block, i = _collect_table(lines, i, section, next_block_num)
        if table_block is not None:
          block_id = _format_block_id(section.section_id, next_block_num)
          next_block_num += 1
          table_block.block_id = block_id
          table_block.order = order
          table_block.metadata.setdefault("section_title", section_title)
          blocks.append(table_block)
          order += 1
        else:
          i += 1
        continue

      # --- Link ---
      if _is_link(stripped):
        block_id = _format_block_id(section.section_id, next_block_num)
        next_block_num += 1
        blocks.append(
          DocumentBlock(
            block_id=block_id,
            section_id=section.section_id,
            type=BlockType.LINK,
            text=stripped,
            order=order,
            metadata={
              "section_title": section_title,
              "section_start_char": offset,
              "section_end_char": offset + len(line),
            },
          ),
        )
        order += 1
        i += 1
        continue

      # --- Note ---
      if _NOTE_RE.match(stripped):
        block_id = _format_block_id(section.section_id, next_block_num)
        next_block_num += 1
        blocks.append(
          DocumentBlock(
            block_id=block_id,
            section_id=section.section_id,
            type=BlockType.NOTE,
            text=stripped,
            order=order,
            metadata={
              "section_title": section_title,
              "section_start_char": offset,
              "section_end_char": offset + len(line),
            },
          ),
        )
        order += 1
        i += 1
        continue

      # --- Quote ---
      if _QUOTE_RE.match(stripped):
        quote_lines, i = _collect_quote_lines(lines, i)
        block_id = _format_block_id(section.section_id, next_block_num)
        next_block_num += 1
        blocks.append(
          DocumentBlock(
            block_id=block_id,
            section_id=section.section_id,
            type=BlockType.QUOTE,
            text="\n".join(stripped for _, stripped in quote_lines),
            order=order,
            metadata={
              "section_title": section_title,
              "section_start_char": quote_lines[0][0],
              "section_end_char": quote_lines[-1][0] + len(quote_lines[-1][1]),
            },
          ),
        )
        order += 1
        continue

      # --- Implicit list (short consecutive lines) ---
      if _is_implicit_list_start(stripped, lines, i):
        implicit_items, i = _collect_implicit_list_items(lines, i)
        block_id = _format_block_id(section.section_id, next_block_num)
        next_block_num += 1
        list_block = DocumentBlock(
          block_id=block_id,
          section_id=section.section_id,
          type=BlockType.LIST,
          text="",
          order=order,
          metadata={"section_title": section_title},
          children=[
            DocumentBlock(
              block_id=_format_block_id(
                section.section_id, next_block_num + ci,
              ),
              section_id=section.section_id,
              type=BlockType.LIST_ITEM,
              text=text,
              order=order + ci + 1,
              metadata={
                "section_title": section_title,
                "section_start_char": off,
                "section_end_char": off + len(txt),
              },
            )
            for ci, (off, txt, text) in enumerate(implicit_items)
          ],
        )
        for child in list_block.children:
          child.parent_block_id = block_id
        next_block_num += len(implicit_items)
        blocks.append(list_block)
        order += 1 + len(implicit_items)
        continue

      # --- Paragraph (collect consecutive non-special lines) ---
      para_lines, i = _collect_paragraph_lines(lines, i)
      block_id = _format_block_id(section.section_id, next_block_num)
      next_block_num += 1
      para_text = "\n".join(
        txt for _, _, txt in para_lines
      )
      blocks.append(
        DocumentBlock(
          block_id=block_id,
          section_id=section.section_id,
          type=BlockType.PARAGRAPH,
          text=para_text,
          order=order,
          metadata={
            "section_title": section_title,
            "section_start_char": para_lines[0][0],
            "section_end_char": para_lines[-1][0] + len(para_lines[-1][2]),
          },
        ),
      )
      order += 1
      continue

    return blocks, order


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _iter_line_entries(text: str) -> list[tuple[int, str]]:
  entries: list[tuple[int, str]] = []
  offset = 0
  for line in text.split("\n"):
    entries.append((offset, line))
    offset += len(line) + 1
  return entries


def _format_block_id(section_id: str, sequence: int) -> str:
  return f"{section_id}_B{sequence:03d}"


def _line_matches_heading(stripped: str, section_title: str) -> bool:
  """Check if a line matches the section title (heading)."""
  if stripped == section_title:
    return True
  if section_title in stripped or stripped in section_title:
    return True
  return bool(
    _HEADING_LIKE_RE.match(stripped)
    and len(stripped.split()) <= _MAX_HEADING_WORDS
    and not stripped.endswith(".")
  )


def _extract_list_marker(line: str) -> str | None:
  numbered = _NUMBERED_RE.match(line)
  if numbered is not None:
    return numbered.group(0).strip()
  bullet = _BULLET_RE.match(line)
  if bullet is not None:
    return bullet.group(0).strip()
  return None


def _is_link(stripped: str) -> bool:
  return bool(_URL_RE.search(stripped))


def _is_table_row(stripped: str) -> bool:
  return bool(_TABLE_RE.match(stripped))


def _is_implicit_list_start(
  line: str,
  all_lines: list[tuple[int, str]],
  index: int,
) -> bool:
  """Check if a line starts an implicit (unmarked) list."""
  words = line.split()
  if len(words) > _MAX_IMPLICIT_LIST_WORDS:
    return False
  if line.endswith((".", "!", "?", ":", ";")):
    return False
  # Need at least one more short line following
  next_idx = index + 1
  while next_idx < len(all_lines):
    n_offset, n_line = all_lines[next_idx]
    n_stripped = n_line.strip()
    if not n_stripped:
      next_idx += 1
      continue
    n_words = n_stripped.split()
    if len(n_words) > _MAX_IMPLICIT_LIST_WORDS:
      return False
    return not n_stripped.endswith((".", "!", "?", ":", ";"))
  return False


def _is_implicit_list_item(line: str) -> bool:
  words = line.split()
  if len(words) > _MAX_IMPLICIT_LIST_WORDS:
    return False
  if line.endswith((".", "!", "?", ":", ";")):
    return False
  return bool(line.strip())


def _collect_list_items(
  lines: list[tuple[int, str]],
  start: int,
  section: Section,
  next_block_num: int,
) -> tuple[list[DocumentBlock], int]:
  items: list[DocumentBlock] = []
  i = start
  ci = 0
  while i < len(lines):
    _offset, line = lines[i]
    stripped = line.strip()
    if not stripped:
      i += 1
      break
    marker = _extract_list_marker(stripped)
    if marker is None:
      break
    # Collect continuation lines for this list item
    item_text = stripped
    i += 1
    while i < len(lines):
      n_offset, n_line = lines[i]
      n_stripped = n_line.strip()
      if not n_stripped:
        break
      if _extract_list_marker(n_stripped) is not None:
        break
      if _is_table_row(n_stripped) or _is_link(n_stripped) or _NOTE_RE.match(n_stripped):
        break

      # Stop if the next line is a standalone sentence (not continuation)
      if (
        n_stripped
        and n_stripped[0].isupper()
        and n_stripped.rstrip().endswith((".", "!", "?"))
      ):
        break
      # continuation line (wrapped text)
      item_text += " " + n_stripped
      i += 1
    items.append(
      DocumentBlock(
        block_id=_format_block_id(section.section_id, next_block_num + ci),
        section_id=section.section_id,
        type=BlockType.LIST_ITEM,
        text=item_text,
        order=0,
        metadata={"section_start_char": _offset},
      ),
    )
    ci += 1
  return items, i


def _collect_table(
  lines: list[tuple[int, str]],
  start: int,
  section: Section,
  next_block_num: int,
) -> tuple[DocumentBlock | None, int]:
  rows: list[DocumentBlock] = []
  i = start
  ri = 0
  while i < len(lines):
    _offset, line = lines[i]
    stripped = line.strip()
    if not stripped or not _TABLE_RE.match(stripped):
      break
    cells = [
      DocumentBlock(
        block_id=_format_block_id(section.section_id, next_block_num + ri * 100 + ci),
        section_id=section.section_id,
        type=BlockType.TABLE_CELL,
        text=cell.strip(),
        order=ri * 100 + ci,
        metadata={},
        children=[],
      )
      for ci, cell in enumerate(stripped.split("|")[1:-1])
    ]
    rows.append(
      DocumentBlock(
        block_id=_format_block_id(section.section_id, next_block_num + ri),
        section_id=section.section_id,
        type=BlockType.TABLE_ROW,
        text=stripped,
        order=ri,
        metadata={},
        children=cells,
      ),
    )
    ri += 1
    i += 1
  if not rows:
    return None, i
  table_text = "\n".join(row.text for row in rows)
  return DocumentBlock(
    block_id="",
    section_id=section.section_id,
    type=BlockType.TABLE,
    text=table_text,
    order=0,
    metadata={"section_start_char": lines[start][0]},
    children=rows,
  ), i


def _collect_quote_lines(
  lines: list[tuple[int, str]],
  start: int,
) -> tuple[list[tuple[int, str]], int]:
  collected: list[tuple[int, str]] = []
  i = start
  while i < len(lines):
    _offset, line = lines[i]
    stripped = line.strip()
    if not stripped or not _QUOTE_RE.match(stripped):
      break
    collected.append((_offset, line))
    i += 1
  return collected, i


def _collect_implicit_list_items(
  lines: list[tuple[int, str]],
  start: int,
) -> tuple[list[tuple[int, str, str]], int]:
  items: list[tuple[int, str, str]] = []
  i = start
  while i < len(lines):
    _offset, line = lines[i]
    stripped = line.strip()
    if not stripped:
      i += 1
      break
    if not _is_implicit_list_item(stripped):
      break
    items.append((_offset, line, stripped))
    i += 1
  return items, i


def _collect_paragraph_lines(
  lines: list[tuple[int, str]],
  start: int,
) -> tuple[list[tuple[int, str, str]], int]:
  collected: list[tuple[int, str, str]] = []
  i = start
  while i < len(lines):
    _offset, line = lines[i]
    stripped = line.strip()
    if not stripped:
      i += 1
      break
    if _extract_list_marker(stripped) is not None:
      break
    if _TABLE_RE.match(stripped):
      break
    if _is_link(stripped):
      break
    if _NOTE_RE.match(stripped):
      break
    if _QUOTE_RE.match(stripped):
      break
    if (
      _is_implicit_list_item(stripped)
      and not collected
      and _is_implicit_list_start(stripped, lines, i)
    ):
      break
    collected.append((_offset, line, stripped))
    i += 1
  # Fallback: if we collected nothing, take the current line as paragraph
  if not collected and start < len(lines):
    _offset, line = lines[start]
    collected.append((_offset, line, line.strip()))
    i = start + 1
  return collected, i
