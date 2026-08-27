"""LLM-powered retrieval-text generator.

Uses the same ``LLMClient`` protocol as ``LLMClauseAnalyzer`` so the same
injected client (OpenAI, Groq, Ollama, Claude, ...) can back both
enrichment stages.
"""

from __future__ import annotations

import json
from typing import Any

from semantic_graph.retrieval_enrichment.models import RetrievalSummary
from semantic_graph.retrieval_enrichment.prompts import build_summary_prompt
from semantic_graph.retrieval_enrichment.summarizer import RetrievalSummarizer
from semantic_graph.semantic_enrichment.llm_clause_analyzer import LLMClient


class LLMRetrievalSummarizer(RetrievalSummarizer):
  """Generates retrieval-optimised clause rewrites using an injected LLM client.

  Args:
      client: An ``LLMClient``-compatible backend.
  """

  def __init__(self, client: LLMClient) -> None:
    self._client = client

  def summarize(
    self,
    clause_text: str,
    clause_id: str,
    *,
    act: str | None = None,
    section_label: str | None = None,
  ) -> RetrievalSummary:
    """Generate a retrieval-text rewrite of the clause via the LLM."""
    system_prompt, user_prompt = build_summary_prompt(
      clause_text, act=act, section_label=section_label,
    )
    raw = self._client.generate(system_prompt, user_prompt)
    data = _parse_response(raw)
    return RetrievalSummary(clause_id=clause_id, retrieval_text=data["retrieval_text"])


def _parse_response(raw: str) -> dict[str, Any]:
  """Parse and validate the LLM response string.

  Args:
      raw: Raw LLM output (should be valid JSON).

  Returns:
      Parsed dictionary with a ``"retrieval_text"`` key.

  Raises:
      ValueError: If the response is empty, malformed, or missing the field.
  """
  cleaned = raw.strip()
  if not cleaned:
    raise ValueError("LLM returned an empty response.")

  try:
    data = json.loads(cleaned)
  except json.JSONDecodeError as exc:
    raise ValueError(f"Invalid JSON from LLM: {exc}") from exc

  if not isinstance(data, dict):
    raise ValueError("LLM response must be a JSON object.")

  retrieval_text = data.get("retrieval_text")
  if not isinstance(retrieval_text, str) or not retrieval_text.strip():
    raise ValueError("LLM response must contain a non-empty 'retrieval_text' string.")

  return data
