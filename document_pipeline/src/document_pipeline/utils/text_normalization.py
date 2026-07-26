"""Deterministic text normalization helpers for document cleaning."""

import unicodedata

_PDF_LIGATURES: dict[str, str] = {
  "\ufb00": "ff",
  "\ufb01": "fi",
  "\ufb02": "fl",
  "\ufb03": "ffi",
  "\ufb04": "ffl",
}

_MAX_CONSECUTIVE_BLANK_LINES = 2


def normalize_document_text(text: str) -> tuple[str, list[str]]:
  """Apply deterministic normalization to raw document text.

  Returns:
    A tuple of normalized text and notes describing applied transformations.
  """
  notes: list[str] = []
  normalized = text

  line_ending_normalized = _normalize_line_endings(normalized)
  if line_ending_normalized != normalized:
    notes.append("Normalized line endings to LF")
    normalized = line_ending_normalized

  ligature_normalized = _replace_pdf_ligatures(normalized)
  if ligature_normalized != normalized:
    notes.append("Replaced PDF ligatures with standard character sequences")
    normalized = ligature_normalized

  nfc_normalized = unicodedata.normalize("NFC", normalized)
  if nfc_normalized != normalized:
    notes.append("Applied Unicode NFC normalization")
    normalized = nfc_normalized

  trimmed_lines = [line.rstrip() for line in normalized.split("\n")]
  if trimmed_lines != normalized.split("\n"):
    notes.append("Trimmed trailing whitespace on each line")
  normalized = "\n".join(trimmed_lines)

  collapsed_lines = _collapse_blank_lines(trimmed_lines)
  if collapsed_lines != trimmed_lines:
    notes.append("Collapsed runs of more than two consecutive blank lines")
    normalized = "\n".join(collapsed_lines)

  return normalized, notes


def _normalize_line_endings(text: str) -> str:
  return text.replace("\r\n", "\n").replace("\r", "\n")


def _replace_pdf_ligatures(text: str) -> str:
  for ligature, replacement in _PDF_LIGATURES.items():
    text = text.replace(ligature, replacement)
  return text


def _collapse_blank_lines(lines: list[str]) -> list[str]:
  collapsed: list[str] = []
  blank_run = 0

  for line in lines:
    if line == "":
      blank_run += 1
      if blank_run <= _MAX_CONSECUTIVE_BLANK_LINES:
        collapsed.append("")
      continue

    blank_run = 0
    collapsed.append(line)

  return collapsed
