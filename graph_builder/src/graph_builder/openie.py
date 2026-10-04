"""Ollama OpenIE extractor: subject / predicate / object only."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from graph_builder.exceptions import LLMGraphBuilderError
from graph_builder.graph_prompt import build_openie_system_prompt, build_openie_user_prompt
from graph_builder.llm_graph_builder import LLMClient
from graph_builder.propositions import RawProposition

if TYPE_CHECKING:
  from document_pipeline.models.entity import EntityDocument

_MARKDOWN_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_propositions(
  raw_output: str,
  *,
  document_id: str = "",
  section_titles: dict[str, str] | None = None,
) -> list[RawProposition]:
  """Parse OpenIE JSON. Reject GraphIR-shaped payloads."""
  cleaned = raw_output.strip()
  cleaned = _MARKDOWN_FENCE.sub("", cleaned).strip()
  if not cleaned:
    raise LLMGraphBuilderError("LLM returned an empty response.")
  try:
    data = json.loads(cleaned)
  except json.JSONDecodeError as exc:
    raise LLMGraphBuilderError(f"Invalid JSON from LLM: {exc}") from exc
  if not isinstance(data, dict):
    raise LLMGraphBuilderError("OpenIE payload must be a JSON object.")
  if "nodes" in data or "relationships" in data:
    raise LLMGraphBuilderError("OpenIE output must not be GraphIR.")
  raw_rows = data.get("propositions")
  if not isinstance(raw_rows, list):
    raise LLMGraphBuilderError("'propositions' must be a JSON array.")

  titles = section_titles or {}
  propositions: list[RawProposition] = []
  for index, row in enumerate(raw_rows):
    if not isinstance(row, dict):
      raise LLMGraphBuilderError(f"Proposition at index {index} must be a JSON object.")
    subject = str(row.get("subject") or "").strip()
    predicate = str(row.get("predicate") or "").strip()
    obj = str(row.get("object") or "").strip()
    if not subject or not predicate or not obj:
      raise LLMGraphBuilderError(f"Proposition at index {index} is missing SPO fields.")
    clause_id = str(row.get("clause_id") or row.get("source_chunk_id") or "").strip()
    evidence = str(row.get("evidence") or "").strip()
    confidence_raw = row.get("confidence")
    confidence: float | None
    if isinstance(confidence_raw, (int, float)):
      confidence = float(confidence_raw)
    else:
      confidence = None
    propositions.append(
      RawProposition(
        subject=subject,
        predicate=predicate,
        object=obj,
        evidence=evidence,
        source_clause_id=clause_id,
        document_id=document_id,
        confidence=confidence,
        section_title=titles.get(clause_id, ""),
      ),
    )
  return propositions


class OpenIEExtractor:
  """Calls an LLM for SPO triples; never asks it for GraphIR labels."""

  def __init__(self, llm_client: LLMClient) -> None:
    self._llm_client = llm_client

  def extract(self, entity_document: EntityDocument) -> list[RawProposition]:
    titles = _clause_titles(entity_document)
    raw_output = self._llm_client.generate(
      build_openie_system_prompt(),
      build_openie_user_prompt(entity_document),
    )
    return parse_propositions(
      raw_output,
      document_id=entity_document.metadata.document_id,
      section_titles=titles,
    )


def _clause_titles(entity_document: EntityDocument) -> dict[str, str]:
  titles: dict[str, str] = {}
  for entity_clause in entity_document.entity_clauses:
    clause = entity_clause.contextual_clause.classified_clause.clause
    titles[clause.clause_id] = clause.section_title or ""
  return titles
