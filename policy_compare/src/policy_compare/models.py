"""View-graph models for the policy overlay UI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

NodeKind = Literal["document", "section", "topic", "law_chunk", "cluster"]
NodeStatus = Literal["neutral", "covered", "weak", "missing", "mapped", "extra"]


class ViewNode(BaseModel):
  id: str
  kind: NodeKind
  title: str
  summary: str = ""
  status: NodeStatus = "neutral"
  extra: dict[str, str] = Field(default_factory=dict)


class ViewEdge(BaseModel):
  source: str
  target: str
  type: str


class ViewGraph(BaseModel):
  nodes: list[ViewNode] = Field(default_factory=list)
  edges: list[ViewEdge] = Field(default_factory=list)


class MatchLink(BaseModel):
  policy_section_id: str
  topic_id: str
  score: float


class MatchResult(BaseModel):
  policy: ViewGraph
  ideal: ViewGraph
  links: list[MatchLink] = Field(default_factory=list)


class LawChunk(BaseModel):
  doc_id: str
  title: str
  summary: str
  clause_text: str = ""
  chunk_type: str | None = None
  act: str = ""
  is_mandatory: bool = False
  topic_ids: list[str] = Field(default_factory=list)
