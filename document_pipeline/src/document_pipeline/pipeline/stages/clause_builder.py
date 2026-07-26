"""Stage 5: ClauseBuilder — assembles document blocks into discourse units.

This stage sits between DocumentBlockExtractor and ClauseExtractor.
It applies purely structural rules to group related blocks together
into ClauseCandidates.  It performs NO semantic reasoning, NO verb
detection, and NO legal classification.
"""

from __future__ import annotations

import re
from collections import defaultdict

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.block import BlockDocument, BlockType, DocumentBlock
from document_pipeline.models.candidate import ClauseCandidate, ClauseCandidateDocument

_NEXT_IS_CONTINUATION: frozenset[str] = frozenset({
  "and", "or", "but", "because", "however", "therefore",
  "such", "this", "these", "those", "they", "it",
  "which", "that", "where", "when", "while", "although",
  "if", "unless", "until", "after", "before", "so",
})

_MAX_NAV_WORDS = 3
_MAX_TITLE_WORDS = 6
_MAX_IMPLICIT_ITEM_WORDS = 5


class ClauseBuilder(BaseProcessor[BlockDocument, ClauseCandidateDocument]):
  """Assembles document blocks into coherent discourse units.

  Applies structural rules to group blocks (heading+paragraph,
  intro+list, paragraph continuation, etc.) without any semantic
  or legal reasoning.
  """

  def process(self, input_data: BlockDocument) -> ClauseCandidateDocument:
    candidates: list[ClauseCandidate] = []
    pending_heading: DocumentBlock | None = None
    pending_title_para: DocumentBlock | None = None
    next_candidate_num: dict[str, int] = defaultdict(int)

    def _start_candidate(
      block: DocumentBlock,
      text: str = "",
      extra_block_ids: list[str] | None = None,
      extra_metadata: dict[str, object] | None = None,
    ) -> ClauseCandidate:
      sid = block.section_id
      next_candidate_num[sid] += 1
      cid = f"{sid}_P{next_candidate_num[sid]:03d}"
      bm: dict[str, object] = {}
      # Preserve section_title from block metadata for downstream
      if "section_title" in block.metadata:
        bm["section_title"] = block.metadata["section_title"]
      if extra_metadata:
        bm.update(extra_metadata)
      return ClauseCandidate(
        candidate_id=cid,
        section_id=sid,
        block_ids=[block.block_id] + (extra_block_ids or []),
        text=text or block.text,
        order=len(candidates),
        metadata=bm,
      )

    def _next_block(index: int) -> DocumentBlock | None:
      return input_data.blocks[index + 1] if index + 1 < len(input_data.blocks) else None

    i = 0
    while i < len(input_data.blocks):
      block = input_data.blocks[i]
      next_b = _next_block(i)

      # ------------------------------------------------------------------
      # HEADING
      # ------------------------------------------------------------------
      if block.type == BlockType.HEADING:
        # Rule 1 & 2: standalone heading → skip; heading + paragraph → merge
        if next_b is not None and next_b.type == BlockType.PARAGRAPH:
          pending_heading = block
          i += 1
          continue
        # Two headings in a row or heading + anything else → skip
        i += 1
        continue

      # ------------------------------------------------------------------
      # LINK
      # ------------------------------------------------------------------
      if block.type == BlockType.LINK:
        # Rule 10: links become metadata on adjacent candidate or standalone → skip
        if candidates and _is_adjacent(candidates[-1], block):
          candidates[-1].block_ids.append(block.block_id)
          _add_link_meta(candidates[-1], block)
        i += 1
        continue

      # ------------------------------------------------------------------
      # TABLE
      # ------------------------------------------------------------------
      if block.type == BlockType.TABLE:
        # Rule 9: reference table block ID, don't flatten
        if candidates and _is_adjacent(candidates[-1], block):
          candidates[-1].block_ids.append(block.block_id)
          _add_table_meta(candidates[-1], block)
        i += 1
        continue

      # ------------------------------------------------------------------
      # NOTE
      # ------------------------------------------------------------------
      if block.type == BlockType.NOTE:
        # Rule 8: attach to preceding candidate
        if candidates:
          candidates[-1].block_ids.append(block.block_id)
          _add_note_meta(candidates[-1], block)
        i += 1
        continue

      # ------------------------------------------------------------------
      # PARAGRAPH
      # ------------------------------------------------------------------
      if block.type == BlockType.PARAGRAPH:
        stripped = block.text.strip()

        # Check for navigation (Rule 6): very short, no sentence punctuation
        if _is_nav(stripped) and (next_b is None or next_b.type == BlockType.LINK):
          i += 1
          continue

        # Check for standalone nav paragraph blocks (multiple consecutive short items)
        if _is_nav(stripped) and _is_nav_sequence(input_data.blocks, i):
          i = _skip_nav_sequence(input_data.blocks, i)
          continue

        # Handle pending heading (Rule 2)
        if pending_heading is not None:
          candidate = _start_candidate(
            block,
            extra_metadata={
              "heading": pending_heading.text,
              "heading_block_id": pending_heading.block_id,
            },
          )
          candidate.block_ids.insert(0, pending_heading.block_id)
          candidates.append(candidate)
          pending_heading = None
          i += 1
          continue

        # Titled list item (Rule 3): short line followed by paragraph
        if _is_title_line(stripped) and next_b is not None and next_b.type == BlockType.PARAGRAPH:
          pending_title_para = block
          i += 1
          continue

        if pending_title_para is not None:
          # The current paragraph is the body for the pending title
          candidate = _start_candidate(
            block,
            extra_metadata={
              "title": pending_title_para.text.strip().rstrip("."),
              "title_block_id": pending_title_para.block_id,
            },
          )
          candidate.block_ids.insert(0, pending_title_para.block_id)
          candidates.append(candidate)
          pending_title_para = None
          i += 1
          continue

        # Paragraph continuation (Rule 7)
        if candidates and _is_continuation(candidates[-1], block):
          candidates[-1].text = candidates[-1].text.rstrip() + " " + block.text
          candidates[-1].block_ids.append(block.block_id)
          i += 1
          continue

        # Start a new candidate
        candidates.append(_start_candidate(block))
        i += 1
        continue

      # ------------------------------------------------------------------
      # LIST
      # ------------------------------------------------------------------
      if block.type == BlockType.LIST:
        # Rule 5: Country lists / implicit lists without verbs → skip
        if _is_implicit_list(block):
          i += 1
          continue

        # Rule 4: Bullet list with introductory paragraph → merge with preceding candidate
        if candidates and _is_adjacent(candidates[-1], block):
          list_text = _format_list_text(block)
          if list_text:
            candidates[-1].text = candidates[-1].text.rstrip() + "\n" + list_text
          candidates[-1].block_ids.append(block.block_id)
          i += 1
          continue

        # Standalone explicit list → create candidate from items
        list_text = _format_list_text(block)
        if list_text:
          candidates.append(_start_candidate(block, text=list_text))
        i += 1
        continue

      # ------------------------------------------------------------------
      # QUOTE, CODE, UNKNOWN — skip
      # ------------------------------------------------------------------
      i += 1

    return ClauseCandidateDocument(
      metadata=input_data.metadata,
      candidates=candidates,
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _is_adjacent(candidate: ClauseCandidate, block: DocumentBlock) -> bool:
  """Check if a block is adjacent to the last block of a candidate.

  Since we process blocks in order, any block reached after a candidate
  has been started is adjacent to it.
  """
  return bool(candidate.block_ids)


def _is_nav(text: str) -> bool:
  """Check if a paragraph is navigation-like (Rule 6)."""
  words = text.split()
  if len(words) > _MAX_NAV_WORDS:
    return False
  if text.endswith((".", "!", "?", ":")):
    return False
  if len(words) == 1 and len(words[0]) <= 2:
    return True
  return text[0].islower() or (text[0].isupper() and len(words) <= 2)


def _is_nav_sequence(blocks: list[DocumentBlock], index: int) -> bool:
  """Check if this block is part of a navigation sequence (consecutive short items)."""
  count = 0
  for j in range(index, min(index + 5, len(blocks))):
    b = blocks[j]
    if b.type == BlockType.PARAGRAPH and _is_nav(b.text.strip()):
      count += 1
    elif b.type == BlockType.LINK:
      continue
    else:
      break
  return count >= 2


def _skip_nav_sequence(blocks: list[DocumentBlock], index: int) -> int:
  """Skip past a navigation sequence."""
  j = index
  while j < len(blocks):
      b = blocks[j]
      if (b.type == BlockType.PARAGRAPH and _is_nav(b.text.strip())) or b.type == BlockType.LINK:
        j += 1
      else:
        break
  return j


def _is_title_line(text: str) -> bool:
  """Check if a paragraph is a titled list item header (Rule 3).

  A title line is a short phrase (≤_MAX_TITLE_WORDS words) that looks
  like a heading or label rather than a complete sentence.
  Paragraphs ending with a period and having 3+ words are excluded
  (they are complete sentences, not titles).
  """
  words = text.split()
  if len(words) > _MAX_TITLE_WORDS:
    return False
  if text.endswith((".", "!", "?")) and len(words) >= 3:
    return False
  clean = text.rstrip(".")
  return len(clean.split()) <= _MAX_TITLE_WORDS and len(clean) > 1


_SENTENCE_END = re.compile(r"[.!?]\s*$")


def _ends_sentence(text: str) -> bool:
  return bool(_SENTENCE_END.search(text))


def _is_continuation(candidate: ClauseCandidate, block: DocumentBlock) -> bool:
  """Check if *block* continues *candidate* (Rule 7)."""
  prev_text = candidate.text.strip()
  if _ends_sentence(prev_text) and not prev_text.endswith(":"):
    return False
  next_stripped = block.text.strip()
  if not next_stripped:
    return False
  first_word = next_stripped.split()[0].lower().strip("(")
  return first_word in _NEXT_IS_CONTINUATION


def _is_implicit_list(block: DocumentBlock) -> bool:
  """Check if a LIST block is an implicit (unmarked) list (Rule 5).

  Relies on the ``is_implicit`` metadata flag set by DocumentBlockExtractor.
  Falls back to heuristic if the flag is absent.
  """
  implicit_flag = block.metadata.get("is_implicit")
  if isinstance(implicit_flag, bool):
    return implicit_flag
  # Fallback heuristic: no children or all items are short and unmarked
  if not block.children:
    return True
  for child in block.children:
    if child.type != BlockType.LIST_ITEM:
      continue
    text = child.text.strip()
    if text.startswith(("-", "*", "•", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "(")):
      return False
    if len(text.split()) > _MAX_IMPLICIT_ITEM_WORDS:
      return False
  return True


def _format_list_text(block: DocumentBlock) -> str:
  """Format a LIST block's items into a single text block."""
  texts: list[str] = []
  for child in block.children:
    if child.type == BlockType.LIST_ITEM:
      t = child.text.strip()
      if t:
        texts.append(t)
  return "\n".join(texts)


def _add_link_meta(candidate: ClauseCandidate, block: DocumentBlock) -> None:
  links: list[str] = []
  existing = candidate.metadata.get("link_block_ids")
  if isinstance(existing, list):
    links = list(existing)
  links.append(block.block_id)
  candidate.metadata["link_block_ids"] = links


def _add_table_meta(candidate: ClauseCandidate, block: DocumentBlock) -> None:
  tables: list[str] = []
  existing = candidate.metadata.get("table_block_ids")
  if isinstance(existing, list):
    tables = list(existing)
  tables.append(block.block_id)
  candidate.metadata["table_block_ids"] = tables


def _add_note_meta(candidate: ClauseCandidate, block: DocumentBlock) -> None:
  notes: list[str] = []
  existing = candidate.metadata.get("note_block_ids")
  if isinstance(existing, list):
    notes = list(existing)
  notes.append(block.block_id)
  candidate.metadata["note_block_ids"] = notes
