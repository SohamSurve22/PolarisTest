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
# Sentence-case headings are extremely common in real-world policies
# ("To provide you with the Firefox browser", "How is your data used?") —
# only the first word is capitalized, unlike _TITLE_CASE_HEADING above which
# requires every word capitalized. Capped at a modest word count so this
# doesn't start matching ordinary paragraph-length sentences.
_SENTENCE_CASE_HEADING = re.compile(
  r"^[A-Z][A-Za-z0-9'&()/\-]*(?:\s+[A-Za-z0-9'&()/\-]+){0,11}[?]?\s*$",
)
_MAX_STANDALONE_WORDS = 12

_MAX_HEADING_LENGTH = 120
_MIN_STANDALONE_LENGTH = 3
_MAX_STANDALONE_LENGTH = 80

# A "list item" heading is a short, standalone-style line (e.g. a single country
# name in a vertical list). Runs of such headings are collapsed into one section.
_LIST_ITEM_MAX_WORDS = 2


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

    return self._collapse_list_runs(text, headings)

  def _collapse_list_runs(
    self,
    text: str,
    headings: list[DetectedHeading],
  ) -> list[DetectedHeading]:
    """Collapse runs of consecutive list-style headings into a single section.

    A vertical list of countries (one name per line) is detected as several
    standalone/uppercase headings.  Such runs have no body text between them,
    so they are collapsed into one section.

    * If the run follows another (kept) section heading, every item -- including
      the first -- is demoted to body text, so the list stays part of its
      enclosing section and inherits that section's real title (e.g.
      "Region Specific Information") instead of being titled with a country name.
    * If the run starts at the top of the document (no preceding kept heading),
      the first item is kept as the section title and the rest become body text.

    Headings separated by real body paragraphs are not adjacent and are left
    untouched, so genuine headings (e.g. FAQ questions followed by answers) are
    preserved.
    """
    if len(headings) < 2:
      return headings

    keep = [True] * len(headings)
    i = 0
    while i < len(headings):
      if not self._is_list_run_candidate(headings[i]):
        i += 1
        continue

      run_end = i
      while (
        run_end + 1 < len(headings)
        and self._is_list_run_candidate(headings[run_end + 1])
        and _only_blank_lines_between(text, headings[run_end], headings[run_end + 1])
      ):
        run_end += 1

      if run_end > i:
        # If the run follows another (kept) section heading, the whole list
        # belongs to that enclosing section: demote every item, including the
        # first, to body text so the list keeps its real contextual title
        # (e.g. "Region Specific Information") rather than a country name.
        # Only when the run starts at the top of the document (no preceding
        # kept heading) do we keep the first item as the section title.
        preceded_by_kept = any(keep[k] for k in range(i - 1, -1, -1))
        drop_from = i if preceded_by_kept else i + 1
        for k in range(drop_from, run_end + 1):
          keep[k] = False

      i = run_end + 1

    return [heading for heading, kept in zip(headings, keep) if kept]

  def _is_list_run_candidate(self, heading: DetectedHeading) -> bool:
    """Return True if *heading* looks like a single item in a vertical list."""
    if heading.heading_style not in (HeadingStyle.STANDALONE, HeadingStyle.UPPERCASE):
      return False
    return len(heading.title.split()) <= _LIST_ITEM_MAX_WORDS

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


def _only_blank_lines_between(
  text: str,
  first: DetectedHeading,
  second: DetectedHeading,
) -> bool:
  """Return True if only blank lines lie between two adjacent headings."""
  line_end = text.find("\n", first.start_char)
  if line_end == -1:
    line_end = len(text)
  return text[line_end:second.start_char].strip() == ""


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

  if len(line.split()) > _MAX_STANDALONE_WORDS:
    return False

  is_title_case = _TITLE_CASE_HEADING.match(line) is not None
  is_sentence_case = _SENTENCE_CASE_HEADING.match(line) is not None
  if not is_title_case and not is_sentence_case:
    return False

  previous_blank = previous_line is None or previous_line.strip() == ""
  next_ok = (
    next_line is None
    or next_line.strip() == ""
    or _looks_like_body_line(next_line)
  )
  return previous_blank and next_ok


def _looks_like_body_line(line: str) -> bool:
  """True if *line* is a paragraph, not another short heading."""
  stripped = line.strip()
  if not stripped:
    return False
  if stripped.endswith((".", "?", "!")) and len(stripped.split()) >= 4:
    return True
  return len(stripped.split()) > _MAX_STANDALONE_WORDS