"""LLM-powered graph builder — converts EntityDocument into GraphIR."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

from graph_builder.exceptions import LLMGraphBuilderError
from graph_builder.graph_ir import GraphIR
from graph_builder.graph_prompt import build_system_prompt, build_user_prompt

if TYPE_CHECKING:
  from document_pipeline.models.entity import EntityDocument

_MARKDOWN_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class LLMClient(Protocol):
  """Protocol for injectable LLM backends."""

  def generate(self, system_prompt: str, user_prompt: str) -> str:
    """Generate a text completion from the given prompts.

    Args:
      system_prompt: System-level instructions.
      user_prompt: User-level input payload.

    Returns:
      Raw model output string.
    """


def parse_llm_response(raw_output: str) -> GraphIR:
  """Parse and normalize raw LLM output into a ``GraphIR``.

  Strips optional markdown code fences before JSON parsing.

  Args:
    raw_output: Raw string returned by the LLM.

  Returns:
    Parsed ``GraphIR`` instance.

  Raises:
    LLMGraphBuilderError: If the output cannot be parsed into valid GraphIR.
  """
  cleaned = raw_output.strip()
  cleaned = _MARKDOWN_FENCE.sub("", cleaned).strip()

  if not cleaned:
    raise LLMGraphBuilderError("LLM returned an empty response.")

  return GraphIR.from_json(cleaned)


class LLMGraphBuilder:
  """Builds graph IR from an ``EntityDocument`` using an injected LLM client."""

  def __init__(self, llm_client: LLMClient) -> None:
    """Initialize the builder with an LLM client.

    Args:
      llm_client: Injectable LLM backend implementing ``LLMClient``.
    """
    self._llm_client = llm_client

  def build(self, entity_document: EntityDocument) -> GraphIR:
    """Convert an entity document into graph IR via the LLM.

    Args:
      entity_document: Structured output from the semantic pipeline.

    Returns:
      Parsed graph intermediate representation.

    Raises:
      LLMGraphBuilderError: If the LLM response cannot be parsed.
    """
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(entity_document)

    raw_output = self._llm_client.generate(system_prompt, user_prompt)
    return parse_llm_response(raw_output)

  def build_from_json(self, entity_document: EntityDocument, graph_json: str) -> GraphIR:
    """Parse pre-generated LLM JSON without calling the LLM.

    Useful for testing and replay workflows.

    Args:
      entity_document: Source document (used for traceability only).
      graph_json: Raw GraphIR JSON string.

    Returns:
      Parsed graph intermediate representation.
    """
    _ = entity_document
    return parse_llm_response(graph_json)
