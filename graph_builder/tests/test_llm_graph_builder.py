"""Tests for LLM graph builder and output parsing."""

import pytest

from graph_builder.exceptions import LLMGraphBuilderError
from graph_builder.graph_ir import GraphIR
from graph_builder.llm_graph_builder import LLMGraphBuilder, parse_llm_response
from tests.conftest import sample_graph_json


class FakeLLMClient:
  """Test double for LLMClient protocol."""

  def __init__(self, response: str) -> None:
    self.response = response
    self.calls: list[tuple[str, str]] = []

  def generate(self, system_prompt: str, user_prompt: str) -> str:
    self.calls.append((system_prompt, user_prompt))
    return self.response


class TestParseLLMResponse:
  def test_parses_raw_json(self) -> None:
    graph_ir = parse_llm_response(sample_graph_json())
    assert isinstance(graph_ir, GraphIR)
    assert len(graph_ir.nodes) == 3

  def test_strips_markdown_fences(self) -> None:
    fenced = f"```json\n{sample_graph_json()}\n```"
    graph_ir = parse_llm_response(fenced)
    assert len(graph_ir.nodes) == 3

  def test_rejects_empty_response(self) -> None:
    with pytest.raises(LLMGraphBuilderError, match="empty"):
      parse_llm_response("   ")


class TestLLMGraphBuilder:
  def test_build_calls_llm_and_parses_response(self) -> None:
    client = FakeLLMClient(sample_graph_json())
    builder = LLMGraphBuilder(client)

    from document_pipeline.models.entity import EntityDocument
    from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata

    entity_doc = EntityDocument(
      metadata=DocumentMetadata(
        document_id="DOC_test",
        filename="act.txt",
        format=DocumentFormat.TXT,
      ),
    )

    graph_ir = builder.build(entity_doc)

    assert len(client.calls) == 1
    system_prompt, user_prompt = client.calls[0]
    assert "APPROVED NODE LABELS" in system_prompt
    assert "DOC_test" in user_prompt
    assert len(graph_ir.nodes) == 3

  def test_build_from_json_skips_llm_call(self) -> None:
    client = FakeLLMClient("")
    builder = LLMGraphBuilder(client)

    from document_pipeline.models.entity import EntityDocument
    from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata

    entity_doc = EntityDocument(
      metadata=DocumentMetadata(
        document_id="DOC_test",
        filename="act.txt",
        format=DocumentFormat.TXT,
      ),
    )

    graph_ir = builder.build_from_json(entity_doc, sample_graph_json())
    assert client.calls == []
    assert len(graph_ir.nodes) == 3
