"""Bridge model between document_pipeline's Clause output and embedding storage.

document_pipeline's Clause model has clause_text, section_title, clause_number,
etc. This module is the one place responsible for turning a Clause into text
worth embedding, so that logic doesn't get buried inside the embedding loop.

LLM-generated retrieval_text (semantic_graph.retrieval_enrichment) is not wired
yet — we embed a section-title + clause-text join until that decision is made.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from document_pipeline.models.clause import Clause


class EmbeddableRecord(BaseModel):
  """A single unit of text to embed, plus the metadata to store alongside it."""

  clause_id: str
  document_id: str
  section_id: str
  section_title: str | None = None
  clause_number: str | None = None
  clause_text: str
  retrieval_text: str = Field(
    description="Text actually sent to the embedding model.",
  )
  source: dict = Field(
    default_factory=dict,
    description="Original clause payload, stored in the Qdrant point payload "
    "for traceability and future re-embedding.",
  )


def clause_to_embeddable(
  clause: Clause,
  *,
  chunk_text: str | None = None,
  chunk_index: int = 0,
) -> EmbeddableRecord:
  """Build an EmbeddableRecord from a document_pipeline Clause.

  Embeds a plain section-title + clause-text join. Pass ``chunk_text`` when
  a long clause has been split; ``clause_text`` on the record stays the
  original clause. A richer retrieval_text rewrite can be swapped in later
  without touching the embedding loop.
  """
  embed_text = (chunk_text if chunk_text is not None else clause.clause_text).strip()
  parts = []
  if clause.section_title:
    parts.append(clause.section_title.strip())
  parts.append(embed_text)
  retrieval_text = " — ".join(p for p in parts if p)

  source = clause.model_dump(mode="json")
  source["chunk_index"] = chunk_index

  return EmbeddableRecord(
    clause_id=clause.clause_id,
    document_id=clause.document_id,
    section_id=clause.section_id,
    section_title=clause.section_title,
    clause_number=clause.clause_number,
    clause_text=clause.clause_text,
    retrieval_text=retrieval_text,
    source=source,
  )


class SearchHit(BaseModel):
  """One kNN result from Qdrant, plus the original payload for later KG fields."""

  score: float
  source_type: str = ""
  document_id: str | None = None
  clause_id: str | None = None
  section_id: str | None = None
  clause_text: str | None = None
  retrieval_text: str | None = None
  embedding_model_version: str | None = None
  payload: dict = Field(default_factory=dict)

  @classmethod
  def from_scored_point(cls, point: object) -> SearchHit:
    payload = dict(getattr(point, "payload", None) or {})
    return cls(
      score=float(getattr(point, "score", 0.0)),
      source_type=str(payload.get("source_type") or ""),
      document_id=payload.get("document_id"),
      clause_id=payload.get("clause_id"),
      section_id=payload.get("section_id"),
      clause_text=payload.get("clause_text"),
      retrieval_text=payload.get("retrieval_text"),
      embedding_model_version=payload.get("embedding_model_version"),
      payload=payload,
    )
