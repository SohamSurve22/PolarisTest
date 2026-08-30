"""Statute Q&A models. This package does not score policies or feed /analyze."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RagError(Exception):
  """Qdrant or Ollama is unavailable for Q&A."""


class RagCitation(BaseModel):
  id: str
  title: str = ""
  text: str = ""
  score: float = 0.0


class RagAnswer(BaseModel):
  mode: str
  answer: str
  citations: list[RagCitation] = Field(default_factory=list)
  retrieve_ms: float = 0.0
  generate_ms: float = 0.0
