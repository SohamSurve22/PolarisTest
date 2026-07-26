"""Deterministic heading detection for legal and policy documents."""

import re

from document_pipeline.sectioning.types import DetectedHeading, HeadingStyle

_MARKDOWN_HEADING = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
_NUMBERED_HEADING = re.compile(r"^(?P<number>\d+(?:\.\d+)*)\.?\s+(?P<title>.+?)\s*$")
_ROMAN_HEADING = re.compile(
  r"^(?P<roman>M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))"
  r"\.?\s+(?P<title>.+?)\s*$",
  re.IGNORECASE,
)
_COLON_HEADING = re.compile(r"^(?P<title>[^\n:]{1,80}):\s*$")
_TITLE_CASE_HEADING = re.compile(
  r"^(?P<title>[A-Z][A-Za-z0-9'&()/\-]+(?:\s+[A-Z][A-Za-z0-9'&()/\-]+){0,8})\s*$",
)

_MAX_HEADING_LENGTH = 120
_MIN_STANDALONE_LENGTH = 3
_MAX_STANDALONE_LENGTH = 80


class HeadingDetector:
  """Detects structural headings using deterministic pattern rules."""

  def detect(self, text: str) -> list[DetectedHeading]:
    """Return headings ordered by their position in the document."""
    headings: list[DetectedHeading] = []
    line_entries = _iter_line_entries(text)

    for index, (start_char, line) in enumerate(line_entries):
      detected = self._detect_line(
        line=line,
        start_char=start_char,
        previous_line=line_entries[index - 1][1] if index > 0 else None,
        next_line=line_entries[index + 1][1] if index + 1 < len(line_entries) else None,
      )
      if detected is not None:
        headings.append(detected)

    return headings

  def _detect_line(
    self,
    *,
    line: str,
    start_char: int,
    previous_line: str | None,
    next_line: str | None,
  ) -> DetectedHeading | None:
    stripped = line.strip()
    if not stripped or len(stripped) > _MAX_HEADING_LENGTH:
      return None

    markdown = _MARKDOWN_HEADING.match(stripped)
    if markdown is not None:
      return DetectedHeading(
        title=markdown.group("title"),
        start_char=start_char,
        heading_level=len(markdown.group("marks")),
        heading_style=HeadingStyle.MARKDOWN,
      )

    numbered = _NUMBERED_HEADING.match(stripped)
    if numbered is not None and _looks_like_numbered_heading(numbered.group("title")):
      number = numbered.group("number")
      level = number.count(".") + 1
      return DetectedHeading(
        title=stripped,
        start_char=start_char,
        heading_level=level,
        heading_style=HeadingStyle.NUMBERED,
      )

    roman = _ROMAN_HEADING.match(stripped)
    if (
      roman is not None
      and roman.group("roman")
      and _looks_like_roman_heading(roman.group("roman"), roman.group("title"))
    ):
      return DetectedHeading(
        title=stripped,
        start_char=start_char,
        heading_level=1,
        heading_style=HeadingStyle.ROMAN,
      )

    if _is_uppercase_heading(stripped):
      return DetectedHeading(
        title=stripped,
        start_char=start_char,
        heading_level=1,
        heading_style=HeadingStyle.UPPERCASE,
      )

    colon = _COLON_HEADING.match(stripped)
    if colon is not None and _looks_like_colon_heading(colon.group("title")):
      return DetectedHeading(
        title=colon.group("title"),
        start_char=start_char,
        heading_level=1,
        heading_style=HeadingStyle.COLON,
      )

    if _is_standalone_heading(
      stripped,
      previous_line=previous_line,
      next_line=next_line,
    ):
      return DetectedHeading(
        title=stripped,
        start_char=start_char,
        heading_level=1,
        heading_style=HeadingStyle.STANDALONE,
      )

    return None


def _iter_line_entries(text: str) -> list[tuple[int, str]]:
  entries: list[tuple[int, str]] = []
  offset = 0

  for line in text.split("\n"):
    entries.append((offset, line))
    offset += len(line) + 1

  return entries


def _looks_like_numbered_heading(title: str) -> bool:
  if not title or title.endswith("."):
    return False

  words = title.split()
  if not words:
    return False

  first_word = words[0]
  if first_word.isupper() and len(first_word) > 1:
    return True

  return title[0].isupper()


def _looks_like_roman_heading(roman: str, title: str) -> bool:
  if not roman or not title:
    return False

  if not roman.isalpha():
    return False

  return title[0].isupper()


def _is_uppercase_heading(line: str) -> bool:
  letters = [char for char in line if char.isalpha()]
  if len(letters) < 2:
    return False

  if any(char.islower() for char in letters):
    return False

  if line.endswith(".") and len(line.split()) > 8:
    return False

  allowed = set(" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-&.,'()/")
  return all(char in allowed for char in line)


def _looks_like_colon_heading(title: str) -> bool:
  stripped = title.strip()
  if not stripped:
    return False

  if stripped.endswith("."):
    return False

  return sum(1 for char in stripped if char.isalpha()) >= 2


def _is_standalone_heading(
  line: str,
  *,
  previous_line: str | None,
  next_line: str | None,
) -> bool:
  if len(line) < _MIN_STANDALONE_LENGTH or len(line) > _MAX_STANDALONE_LENGTH:
    return False

  if line.endswith("."):
    return False

  if not _TITLE_CASE_HEADING.match(line):
    return False

  previous_blank = previous_line is not None and previous_line.strip() == ""
  next_blank = next_line is not None and next_line.strip() == ""
  return previous_blank and next_blank
