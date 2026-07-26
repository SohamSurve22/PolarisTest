"""Types used by clause segmentation components."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClauseUnit:
  """A clause-sized text unit detected within a section."""

  text: str
  start_char: int
  end_char: int
  clause_number: str | None = None
