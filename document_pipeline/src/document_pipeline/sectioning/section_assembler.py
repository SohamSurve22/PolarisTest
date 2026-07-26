"""Assembles detected headings into section models."""

from document_pipeline.models.metadata import Span
from document_pipeline.models.section import Section
from document_pipeline.sectioning.types import DetectedHeading


class SectionAssembler:
  """Builds ordered sections from detected headings."""

  def assemble(self, full_text: str, headings: list[DetectedHeading]) -> list[Section]:
    """Partition document text into contiguous, non-overlapping sections."""
    if not headings:
      return [
        Section(
          section_id="S001",
          title=None,
          text=full_text,
          span=Span(start=0, end=len(full_text)),
          level=1,
          parent_section_id=None,
        ),
      ]

    sections: list[Section] = []
    level_stack: list[tuple[int, str]] = []
    next_section_number = 1

    if headings[0].start_char > 0:
      section_id = _format_section_id(next_section_number)
      next_section_number += 1
      end_char = headings[0].start_char
      sections.append(
        Section(
          section_id=section_id,
          title=None,
          text=full_text[0:end_char],
          span=Span(start=0, end=end_char),
          level=1,
          parent_section_id=None,
        ),
      )

    for index, heading in enumerate(headings):
      start_char = heading.start_char
      end_char = (
        headings[index + 1].start_char
        if index + 1 < len(headings)
        else len(full_text)
      )

      while level_stack and level_stack[-1][0] >= heading.heading_level:
        level_stack.pop()

      parent_section_id = level_stack[-1][1] if level_stack else None
      section_id = _format_section_id(next_section_number)
      next_section_number += 1

      sections.append(
        Section(
          section_id=section_id,
          title=heading.title,
          text=full_text[start_char:end_char],
          span=Span(start=start_char, end=end_char),
          level=heading.heading_level,
          parent_section_id=parent_section_id,
        ),
      )
      level_stack.append((heading.heading_level, section_id))

    return sections


def _format_section_id(sequence_number: int) -> str:
  return f"S{sequence_number:03d}"
