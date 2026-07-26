"""Tests for Stage 4: DocumentBlockExtractor."""

from document_pipeline.models.block import BlockType
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.section import Section, SectionedDocument
from document_pipeline.pipeline.stages.block_extractor import DocumentBlockExtractor


def _make_sectioned(
  full_text: str,
  *,
  section_id: str = "S001",
  title: str | None = None,
  level: int = 1,
) -> SectionedDocument:
  metadata = DocumentMetadata(
    document_id="doc-block-001",
    filename="test.txt",
    format=DocumentFormat.TXT,
  )
  sections = [
    Section(
      section_id=section_id,
      title=title,
      text=full_text,
      span=Span(start=0, end=len(full_text)),
      level=level,
    ),
  ]
  return SectionedDocument(metadata=metadata, full_text=full_text, sections=sections)


def _find_blocks_by_type(blocks, block_type: BlockType):
  """Recursively find all blocks of a given type."""
  result = []
  for block in blocks:
    if block.type == block_type:
      result.append(block)
    result.extend(_find_blocks_by_type(block.children, block_type))
  return result


# ---------------------------------------------------------------------------
# Block extraction tests
# ---------------------------------------------------------------------------


def test_heading_recognition(block_extractor: DocumentBlockExtractor) -> None:
  """Section title should produce a HEADING block."""
  text = "Data Processing Activities\n\nWe process your data for legitimate purposes."
  sectioned = _make_sectioned(text, title="Data Processing Activities")

  block_doc = block_extractor.process(sectioned)

  headings = _find_blocks_by_type(block_doc.blocks, BlockType.HEADING)
  assert len(headings) == 1
  assert headings[0].text == "Data Processing Activities"
  assert headings[0].section_id == "S001"


def test_paragraph_recognition(block_extractor: DocumentBlockExtractor) -> None:
  """Plain text without structure should produce a PARAGRAPH block."""
  text = "The Partner shall maintain confidentiality of all data."
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  paras = _find_blocks_by_type(block_doc.blocks, BlockType.PARAGRAPH)
  assert len(paras) == 1
  assert paras[0].text == text


def test_paragraph_multi_sentence(block_extractor: DocumentBlockExtractor) -> None:
  """Multiple sentence paragraph should be a single PARAGRAPH block."""
  text = "We collect your email. We process your data. We retain logs for 90 days."
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  paras = _find_blocks_by_type(block_doc.blocks, BlockType.PARAGRAPH)
  assert len(paras) == 1
  assert paras[0].type == BlockType.PARAGRAPH


def test_bullet_list_recognition(block_extractor: DocumentBlockExtractor) -> None:
  """Bullet list items should be grouped under a LIST block."""
  text = "Obligations:\n- Provide notice.\n- Maintain records.\n- Ensure compliance."
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  lists = _find_blocks_by_type(block_doc.blocks, BlockType.LIST)
  items = _find_blocks_by_type(block_doc.blocks, BlockType.LIST_ITEM)
  assert len(lists) == 1
  assert len(items) == 3
  assert items[0].text == "- Provide notice."
  assert items[1].text == "- Maintain records."
  assert items[2].text == "- Ensure compliance."


def test_numbered_list_recognition(block_extractor: DocumentBlockExtractor) -> None:
  """Numbered list items should be grouped under a LIST block."""
  text = "Steps:\n1. Provide notice.\n2. Maintain records.\n3. Ensure compliance."
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  items = _find_blocks_by_type(block_doc.blocks, BlockType.LIST_ITEM)
  assert len(items) == 3
  assert items[0].text == "1. Provide notice."
  assert items[1].text == "2. Maintain records."
  assert items[2].text == "3. Ensure compliance."


def test_country_list_implicit(block_extractor: DocumentBlockExtractor) -> None:
  """Consecutive short lines without markers should be treated as an implicit list."""
  text = "International Data Transfers\n\nAustralia\nBrazil\nCanada\nFrance"
  sectioned = _make_sectioned(text, title="International Data Transfers")

  block_doc = block_extractor.process(sectioned)

  items = _find_blocks_by_type(block_doc.blocks, BlockType.LIST_ITEM)
  assert len(items) == 4
  texts = [item.text for item in items]
  assert "Australia" in texts
  assert "Brazil" in texts
  assert "Canada" in texts
  assert "France" in texts
  # Should NOT be individual paragraphs
  paras = _find_blocks_by_type(block_doc.blocks, BlockType.PARAGRAPH)
  names_in_paras = [
    p.text for p in paras
    if p.text.strip() in ("Australia", "Brazil", "Canada", "France")
  ]
  assert len(names_in_paras) == 0


def test_nested_lists(block_extractor: DocumentBlockExtractor) -> None:
  """Hierarchical list structure should preserve nesting."""
  text = "- Level one\n  - Level two\n  - Level two again\n- Another level one"
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  items = _find_blocks_by_type(block_doc.blocks, BlockType.LIST_ITEM)
  assert len(items) >= 2
  assert items[0].type == BlockType.LIST_ITEM


def test_hyperlink_recognition(block_extractor: DocumentBlockExtractor) -> None:
  """Lines containing URLs should be classified as LINK blocks."""
  text = "Visit https://example.com/policy for details."
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  links = _find_blocks_by_type(block_doc.blocks, BlockType.LINK)
  assert len(links) >= 1
  assert "https://example.com/policy" in links[0].text


def test_table_recognition(block_extractor: DocumentBlockExtractor) -> None:
  """Pipe-delimited lines should be classified as TABLE blocks."""
  text = "| Name | Value |\n| A | 1 |\n| B | 2 |"
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  tables = _find_blocks_by_type(block_doc.blocks, BlockType.TABLE)
  rows = _find_blocks_by_type(block_doc.blocks, BlockType.TABLE_ROW)
  cells = _find_blocks_by_type(block_doc.blocks, BlockType.TABLE_CELL)
  assert len(tables) == 1
  assert len(rows) == 3
  assert len(cells) >= 4


def test_paragraph_after_list(block_extractor: DocumentBlockExtractor) -> None:
  """A paragraph following a list should be correctly classified."""
  text = (
    "- Item one\n"
    "- Item two\n"
    "\n"
    "This is a follow-up paragraph explaining the list."
  )
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  items = _find_blocks_by_type(block_doc.blocks, BlockType.LIST_ITEM)
  paras = _find_blocks_by_type(block_doc.blocks, BlockType.PARAGRAPH)
  assert len(items) == 2
  assert len(paras) == 1
  assert "follow-up paragraph" in paras[0].text


def test_mixed_content_preserves_order(block_extractor: DocumentBlockExtractor) -> None:
  """Block order should match original document order."""
  text = (
    "First paragraph.\n"
    "- List item.\n"
    "Second paragraph.\n"
  )
  sectioned = _make_sectioned(text)

  block_doc = block_extractor.process(sectioned)

  top_types = [b.type for b in block_doc.blocks]
  assert top_types[0] == BlockType.PARAGRAPH
  assert top_types[1] == BlockType.LIST
  assert top_types[2] == BlockType.PARAGRAPH


def test_block_ids_are_stable(block_extractor: DocumentBlockExtractor) -> None:
  """Running the extractor twice should produce identical block IDs."""
  text = "Paragraph one.\n\nParagraph two."
  sectioned = _make_sectioned(text)

  first = block_extractor.process(sectioned)
  second = block_extractor.process(sectioned)

  first_ids = [b.block_id for b in first.blocks]
  second_ids = [b.block_id for b in second.blocks]
  assert first_ids == second_ids
