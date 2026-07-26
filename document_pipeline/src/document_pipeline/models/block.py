"""Block-level models for the DocumentBlockExtractor stage."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from document_pipeline.models.metadata import DocumentMetadata


class BlockType(StrEnum):
  HEADING = "HEADING"
  PARAGRAPH = "PARAGRAPH"
  LIST = "LIST"
  LIST_ITEM = "LIST_ITEM"
  TABLE = "TABLE"
  TABLE_ROW = "TABLE_ROW"
  TABLE_CELL = "TABLE_CELL"
  LINK = "LINK"
  NOTE = "NOTE"
  QUOTE = "QUOTE"
  CODE = "CODE"
  UNKNOWN = "UNKNOWN"


class DocumentBlock(BaseModel):
  block_id: str
  section_id: str
  parent_block_id: str | None = None
  type: BlockType
  text: str
  level: int | None = None
  order: int
  metadata: dict[str, object] = Field(default_factory=dict)
  children: list[DocumentBlock] = Field(default_factory=list)


class BlockDocument(BaseModel):
  metadata: DocumentMetadata
  blocks: list[DocumentBlock] = Field(default_factory=list)
