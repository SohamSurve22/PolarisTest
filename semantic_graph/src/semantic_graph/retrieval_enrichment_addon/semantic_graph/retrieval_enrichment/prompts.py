"""Prompt templates for LLM-based retrieval-text generation."""

from __future__ import annotations

_SYSTEM_PROMPT = (
  "You are a legal document search-indexing assistant. "
  "Rewrite the given legal clause as a single self-contained, plain-English "
  "sentence or two, suitable for semantic search. Name the act and section "
  "explicitly, resolve pronouns and cross-references, and avoid copying the "
  "original legal phrasing verbatim. Return ONLY valid JSON."
)

_USER_TEMPLATE = (
  "Required JSON schema:\n"
  "{{\n"
  '    "retrieval_text": ""\n'
  "}}\n\n"
  "Act: {act}\n"
  "Section: {section_label}\n"
  "Clause:\n\n"
  "{clause_text}"
)


def build_summary_prompt(
  clause_text: str,
  *,
  act: str | None,
  section_label: str | None,
) -> tuple[str, str]:
  """Build the system and user prompt pair for retrieval-text generation.

  Args:
      clause_text:   The raw clause text to rewrite.
      act:           Name of the source act, if known.
      section_label: Section/subsection label, if known.

  Returns:
      A ``(system_prompt, user_prompt)`` tuple.
  """
  return _SYSTEM_PROMPT, _USER_TEMPLATE.format(
    clause_text=clause_text,
    act=act or "unknown",
    section_label=section_label or "unknown",
  )
