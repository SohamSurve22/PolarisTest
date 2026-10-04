"""Tests for OpenIE proposition parsing."""

import json

import pytest

from graph_builder.exceptions import LLMGraphBuilderError
from graph_builder.openie import OpenIEExtractor, parse_propositions
from tests.conftest import sample_graph_json


class FakeLLMClient:
  def __init__(self, response: str) -> None:
    self.response = response
    self.calls: list[tuple[str, str]] = []

  def generate(self, system_prompt: str, user_prompt: str) -> str:
    self.calls.append((system_prompt, user_prompt))
    return self.response


def _spo_json() -> str:
  return json.dumps(
    {
      "propositions": [
        {
          "subject": "we",
          "predicate": "collect",
          "object": "your email address",
          "evidence": "We collect your email address to provide our services.",
          "clause_id": "S001_C001",
          "confidence": 0.9,
        },
      ],
    },
  )


class TestParsePropositions:
  def test_parses_spo_json(self) -> None:
    rows = parse_propositions(_spo_json(), document_id="DOC_x")
    assert len(rows) == 1
    assert rows[0].predicate.lower() == "collect"
    assert "email" in rows[0].object.lower()
    assert rows[0].evidence.startswith("We collect")
    assert rows[0].source_clause_id == "S001_C001"

  def test_rejects_graphir_shaped_output(self) -> None:
    with pytest.raises(LLMGraphBuilderError, match="GraphIR"):
      parse_propositions(sample_graph_json())

  def test_strips_markdown_fences(self) -> None:
    rows = parse_propositions(f"```json\n{_spo_json()}\n```")
    assert len(rows) == 1


class TestOpenIEExtractor:
  def test_extract_calls_llm_with_openie_prompt(self) -> None:
    from document_pipeline.models.clause import Clause
    from document_pipeline.models.context import ContextualClause
    from document_pipeline.models.entity import EntityClause, EntityDocument
    from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
    from document_pipeline.models.semantic import ClassifiedClause, StructuralRole

    clause = Clause(
      clause_id="S001_C001",
      section_id="S001",
      section_title="Collection",
      document_id="DOC_x",
      document_type=DocumentFormat.TXT,
      clause_text="We collect your email address to provide our services.",
      span=Span(start=0, end=54),
    )
    document = EntityDocument(
      metadata=DocumentMetadata(
        document_id="DOC_x",
        filename="policy.txt",
        format=DocumentFormat.TXT,
      ),
      entity_clauses=[
        EntityClause(
          contextual_clause=ContextualClause(
            classified_clause=ClassifiedClause(
              clause=clause,
              role=StructuralRole.STATEMENT,
              confidence=1.0,
              classification_reason=[],
            ),
          ),
          entities=[],
        ),
      ],
    )
    client = FakeLLMClient(_spo_json())
    rows = OpenIEExtractor(client).extract(document)
    assert len(client.calls) == 1
    system_prompt, user_prompt = client.calls[0]
    assert "GraphIR" not in system_prompt or "Do NOT invent" in system_prompt
    assert "propositions" in system_prompt
    assert "DOC_x" in user_prompt
    assert rows[0].section_title == "Collection"
