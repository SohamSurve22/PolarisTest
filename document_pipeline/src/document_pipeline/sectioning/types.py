"""Types used by the section extraction components."""

from dataclasses import dataclass
from enum import StrEnum


class HeadingStyle(StrEnum):
  """Detected heading presentation style."""

  MARKDOWN = "markdown"
  NUMBERED = "numbered"
  ROMAN = "roman"
  UPPERCASE = "uppercase"
  COLON = "colon"
  STANDALONE = "standalone"


@dataclass(frozen=True)
class DetectedHeading:
  """A heading identified within cleaned document text."""

  title: str
  start_char: int
  heading_level: int
  heading_style: HeadingStyle
