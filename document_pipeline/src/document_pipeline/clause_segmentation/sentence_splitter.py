"""Deterministic sentence and list-item splitting."""

import re

from document_pipeline.clause_segmentation.types import ClauseUnit

_PROTECTED_PERIOD = "\uE000"

_ABBREVIATIONS: tuple[str, ...] = (
  "e.g.",
  "i.e.",
  "etc.",
  "et al.",
  "vs.",
  "Mr.",
  "Mrs.",
  "Ms.",
  "Dr.",
  "Prof.",
  "Sr.",
  "Jr.",
  "Inc.",
  "Ltd.",
  "Corp.",
  "Sec.",
  "No.",
  "Art.",
  "para.",
  "U.S.C.",
  "U.S.",
  "U.K.",
  "St.",
)

_NUMBERED_LIST_ITEM = re.compile(
  r"^\s*(?P<number>(?:\(\d+\)|\d+(?:\.\d+)*[.)]|[A-Za-z][.)]|\([A-Za-z]\)))\s+(?P<body>.+)$",
)
_BULLET_LIST_ITEM = re.compile(r"^\s*(?P<bullet>[-*•])\s+(?P<body>.+)$")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class SentenceSplitter:
  """Splits section text into sentence-level and list-item clause units."""

  def split(self, section_text: str) -> list[ClauseUnit]:
    """Return ordered clause units preserving the original section text."""
    if not section_text:
      return []

    units: list[ClauseUnit] = []
    line_entries = _iter_line_entries(section_text)
    index = 0

    while index < len(line_entries):
      start_offset, line = line_entries[index]
      if not line.strip():
        index += 1
        continue

      list_number = _extract_list_number(line)
      if list_number is not None:
        units.append(
          ClauseUnit(
            text=line,
            start_char=start_offset,
            end_char=start_offset + len(line),
            clause_number=list_number,
          ),
        )
        index += 1
        continue

      block_start = start_offset
      block_end = start_offset + len(line)
      index += 1

      while index < len(line_entries):
        next_offset, next_line = line_entries[index]
        if not next_line.strip():
          break
        if _extract_list_number(next_line) is not None:
          break

        block_end = next_offset + len(next_line)
        index += 1

      block_text = section_text[block_start:block_end]
      units.extend(_split_prose_block(block_text, block_start))

    return units


def _iter_line_entries(text: str) -> list[tuple[int, str]]:
  entries: list[tuple[int, str]] = []
  offset = 0

  for line in text.split("\n"):
    entries.append((offset, line))
    offset += len(line) + 1

  return entries


def _extract_list_number(line: str) -> str | None:
  numbered = _NUMBERED_LIST_ITEM.match(line)
  if numbered is not None:
    return numbered.group("number")

  bullet = _BULLET_LIST_ITEM.match(line)
  if bullet is not None:
    return bullet.group("bullet")

  return None


def _split_prose_block(block_text: str, block_start: int) -> list[ClauseUnit]:
  if not block_text.strip():
    return []

  protected = _protect_periods(block_text)
  spans = _sentence_spans(protected)
  units: list[ClauseUnit] = []

  for rel_start, rel_end in spans:
    sentence = _restore_periods(protected[rel_start:rel_end])
    if not sentence.strip():
      continue

    units.append(
      ClauseUnit(
        text=sentence,
        start_char=block_start + rel_start,
        end_char=block_start + rel_end,
        clause_number=None,
      ),
    )

  return units


def _sentence_spans(text: str) -> list[tuple[int, int]]:
  spans: list[tuple[int, int]] = []
  start = 0

  for match in _SENTENCE_BOUNDARY.finditer(text):
    end = match.start()
    spans.append((start, end))
    start = match.end()

  spans.append((start, len(text)))
  return spans


def _protect_periods(text: str) -> str:
  protected = text
  for abbreviation in sorted(_ABBREVIATIONS, key=len, reverse=True):
    protected = protected.replace(
      abbreviation,
      abbreviation.replace(".", _PROTECTED_PERIOD),
    )

  return re.sub(r"(\d)\.(\d)", rf"\1{_PROTECTED_PERIOD}\2", protected)


def _restore_periods(text: str) -> str:
  return text.replace(_PROTECTED_PERIOD, ".")
