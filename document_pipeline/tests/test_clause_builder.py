"""Tests for Stage 5: ClauseBuilder."""

from document_pipeline.models.block import BlockDocument, BlockType, DocumentBlock
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.clause_builder import ClauseBuilder


def _make_block(
  text: str,
  *,
  block_type: BlockType = BlockType.PARAGRAPH,
  section_id: str = "S001",
  order: int = 0,
  block_id: str | None = None,
  section_title: str | None = None,
  children: list[DocumentBlock] | None = None,
) -> DocumentBlock:
  bid = block_id or f"{section_id}_B{order + 1:03d}"
  meta: dict[str, object] = {}
  if section_title:
    meta["section_title"] = section_title
  return DocumentBlock(
    block_id=bid,
    section_id=section_id,
    type=block_type,
    text=text,
    order=order,
    metadata=meta,
    children=children or [],
  )


def _make_block_doc(
  blocks: list[DocumentBlock],
  document_id: str = "doc-builder-001",
) -> BlockDocument:
  metadata = DocumentMetadata(
    document_id=document_id,
    filename="agreement.txt",
    format=DocumentFormat.TXT,
  )
  return BlockDocument(metadata=metadata, blocks=blocks)


# ---------------------------------------------------------------------------
# Rule 1 & 2: Heading + paragraph
# ---------------------------------------------------------------------------


def test_heading_followed_by_paragraph_merges(
  clause_builder: ClauseBuilder,
) -> None:
  blocks = [
    _make_block("Data Processing", block_type=BlockType.HEADING, order=0),
    _make_block("We collect your personal data.", order=1),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  c = result.candidates[0]
  assert c.text == "We collect your personal data."
  assert c.metadata.get("heading") == "Data Processing"
  assert "heading_block_id" in c.metadata
  assert c.section_id == "S001"


def test_standalone_heading_skipped(
  clause_builder: ClauseBuilder,
) -> None:
  blocks = [
    _make_block("Data Processing", block_type=BlockType.HEADING, order=0),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 0


def test_two_headings_in_a_row_skipped(
  clause_builder: ClauseBuilder,
) -> None:
  blocks = [
    _make_block("Heading One", block_type=BlockType.HEADING, order=0),
    _make_block("Heading Two", block_type=BlockType.HEADING, order=1),
    _make_block("Some paragraph.", order=2),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  # Only the last heading before paragraph should be used
  assert len(result.candidates) == 1
  assert result.candidates[0].metadata.get("heading") == "Heading Two"


# ---------------------------------------------------------------------------
# Rule 3: Titled list items
# ---------------------------------------------------------------------------


def test_title_line_followed_by_paragraph(
  clause_builder: ClauseBuilder,
) -> None:
  """Short line + paragraph → one candidate with title in metadata."""
  blocks = [
    _make_block("Affiliates.", order=0),
    _make_block("Snap consists of several subsidiaries worldwide.", order=1),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  c = result.candidates[0]
  assert c.text == "Snap consists of several subsidiaries worldwide."
  assert c.metadata.get("title") == "Affiliates"
  assert "title_block_id" in c.metadata


def test_title_line_requires_following_paragraph(
  clause_builder: ClauseBuilder,
) -> None:
  """Short line without following paragraph → stays as standalone candidate."""
  blocks = [
    _make_block("Affiliates.", order=0),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1


# ---------------------------------------------------------------------------
# Rule 4: Bullet list with introductory paragraph
# ---------------------------------------------------------------------------


def test_bullet_list_with_intro_paragraph_merged(
  clause_builder: ClauseBuilder,
) -> None:
  """Intro paragraph + list → merged into one candidate."""
  list_item_1 = _make_block(
    "- Email address", block_type=BlockType.LIST_ITEM, order=1,
  )
  list_item_2 = _make_block(
    "- Phone number", block_type=BlockType.LIST_ITEM, order=2,
  )
  list_block = _make_block(
    "", block_type=BlockType.LIST, order=3,
    children=[list_item_1, list_item_2],
  )
  # Mark as explicit list (matching block extractor behavior)
  list_block.metadata["is_implicit"] = False
  blocks = [
    _make_block("We collect the following:", order=0),
    list_block,
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  c = result.candidates[0]
  assert "We collect the following:" in c.text
  assert "- Email address" in c.text
  assert "- Phone number" in c.text
  # Should reference all block IDs
  assert len(c.block_ids) >= 2


# ---------------------------------------------------------------------------
# Rule 5: Country lists / implicit lists
# ---------------------------------------------------------------------------


def test_implicit_list_skipped(
  clause_builder: ClauseBuilder,
) -> None:
  """Unmarked short-item list → no candidate."""
  items = [
    _make_block("Australia", block_type=BlockType.LIST_ITEM, order=0),
    _make_block("Brazil", block_type=BlockType.LIST_ITEM, order=1),
    _make_block("Canada", block_type=BlockType.LIST_ITEM, order=2),
  ]
  blocks = [
    _make_block("", block_type=BlockType.LIST, order=0, children=items),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 0


# ---------------------------------------------------------------------------
# Rule 6: Navigation
# ---------------------------------------------------------------------------


def test_navigation_paragraph_skipped(
  clause_builder: ClauseBuilder,
) -> None:
  """Short nav-like paragraphs → skipped."""
  blocks = [
    _make_block("Learn more", order=0),
    _make_block("Click here", order=1),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 0


def test_non_nav_paragraph_preserved(
  clause_builder: ClauseBuilder,
) -> None:
  """Paragraphs that look like normal text → not skipped."""
  blocks = [
    _make_block("The Partner shall maintain confidentiality.", order=0),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1


# ---------------------------------------------------------------------------
# Rule 7: Paragraph continuation
# ---------------------------------------------------------------------------


def test_paragraph_continuation_merged(
  clause_builder: ClauseBuilder,
) -> None:
  """Non-sentence-ending paragraph + continuation → merged."""
  blocks = [
    _make_block("The Partner agrees to", order=0),
    _make_block("maintain confidentiality of all data.", order=1),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  assert "maintain confidentiality" in result.candidates[0].text


def test_sentence_ending_breaks_continuation(
  clause_builder: ClauseBuilder,
) -> None:
  """Paragraph ending with . → no merge."""
  blocks = [
    _make_block("The Partner agrees.", order=0),
    _make_block("maintain confidentiality of all data.", order=1),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 2


def test_continuation_with_pronoun(
  clause_builder: ClauseBuilder,
) -> None:
  """Next paragraph starting with 'this' → merged."""
  blocks = [
    _make_block("We process your data for", order=0),
    _make_block("this purpose and related activities.", order=1),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1


def test_continuation_with_conjunction(
  clause_builder: ClauseBuilder,
) -> None:
  """Next paragraph starting with 'and' → merged."""
  blocks = [
    _make_block("We collect your email,", order=0),
    _make_block("and we use it for account verification.", order=1),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1


# ---------------------------------------------------------------------------
# Rule 8: Notes
# ---------------------------------------------------------------------------


def test_note_attached_to_preceding_candidate(
  clause_builder: ClauseBuilder,
) -> None:
  """NOTE blocks → attached to preceding candidate."""
  blocks = [
    _make_block("We collect your personal data.", order=0),
    _make_block(
      "This policy was updated on Jan 1.",
      block_type=BlockType.NOTE, order=1,
    ),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  c = result.candidates[0]
  assert "personal data" in c.text
  assert "note_block_ids" in c.metadata
  assert isinstance(c.metadata["note_block_ids"], list)
  assert len(c.metadata["note_block_ids"]) == 1


# ---------------------------------------------------------------------------
# Rule 9: Tables
# ---------------------------------------------------------------------------


def test_table_referenced_in_metadata(
  clause_builder: ClauseBuilder,
) -> None:
  """TABLE block → referenced by block ID in candidate metadata."""
  blocks = [
    _make_block("See table below for details.", order=0),
    _make_block(
      "Name | Age\nJohn | 30",
      block_type=BlockType.TABLE, order=1,
    ),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  c = result.candidates[0]
  assert "table_block_ids" in c.metadata
  assert isinstance(c.metadata["table_block_ids"], list)
  assert len(c.metadata["table_block_ids"]) == 1


# ---------------------------------------------------------------------------
# Rule 10: Links
# ---------------------------------------------------------------------------


def test_link_referenced_in_metadata(
  clause_builder: ClauseBuilder,
) -> None:
  """LINK block → referenced by block ID in candidate metadata."""
  blocks = [
    _make_block("Read our privacy policy at", order=0),
    _make_block("https://example.com/privacy", block_type=BlockType.LINK, order=1),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  c = result.candidates[0]
  assert "link_block_ids" in c.metadata
  assert isinstance(c.metadata["link_block_ids"], list)
  assert len(c.metadata["link_block_ids"]) == 1


# ---------------------------------------------------------------------------
# Mixed content
# ---------------------------------------------------------------------------


def test_mixed_content_maintains_order(
  clause_builder: ClauseBuilder,
) -> None:
  """Multiple sections and block types → correct ordering and IDs."""
  blocks = [
    _make_block("Section One", block_type=BlockType.HEADING, order=0, section_id="S001"),
    _make_block("Terms and conditions apply.", order=1, section_id="S001"),
    _make_block("Section Two", block_type=BlockType.HEADING, order=2, section_id="S002"),
    _make_block("Additional terms apply.", order=3, section_id="S002"),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 2
  assert result.candidates[0].section_id == "S001"
  assert result.candidates[1].section_id == "S002"
  assert result.candidates[0].order < result.candidates[1].order


# ---------------------------------------------------------------------------
# Section title preservation
# ---------------------------------------------------------------------------


def test_section_title_preserved(
  clause_builder: ClauseBuilder,
) -> None:
  """section_title from block metadata → copied to candidate metadata."""
  blocks = [
    _make_block(
      "Data Processing",
      block_type=BlockType.HEADING, order=0,
      section_title="Data Processing",
    ),
    _make_block(
      "We collect your data.",
      order=1,
      section_title="Data Processing",
    ),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  assert result.candidates[0].metadata.get("section_title") == "Data Processing"


# ---------------------------------------------------------------------------
# Stability and edge cases
# ---------------------------------------------------------------------------


def test_empty_input(
  clause_builder: ClauseBuilder,
) -> None:
  """Empty BlockDocument → empty ClauseCandidateDocument."""
  metadata = DocumentMetadata(
    document_id="doc-builder-001",
    filename="agreement.txt",
    format=DocumentFormat.TXT,
  )
  block_doc = BlockDocument(metadata=metadata, blocks=[])

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 0
  assert result.metadata.document_id == "doc-builder-001"


def test_deterministic_output(
  clause_builder: ClauseBuilder,
) -> None:
  blocks = [
    _make_block("Introduction.", order=0),
    _make_block("Terms apply.", order=1),
  ]
  block_doc = _make_block_doc(blocks)

  first = clause_builder.process(block_doc)
  second = clause_builder.process(block_doc)

  assert first == second


def test_quote_and_code_blocks_skipped(
  clause_builder: ClauseBuilder,
) -> None:
  blocks = [
    _make_block("Some quote text", block_type=BlockType.QUOTE, order=0),
    _make_block("print('hello')", block_type=BlockType.CODE, order=1),
    _make_block("Normal paragraph.", order=2),
  ]
  block_doc = _make_block_doc(blocks)

  result = clause_builder.process(block_doc)

  assert len(result.candidates) == 1
  assert result.candidates[0].text == "Normal paragraph."
