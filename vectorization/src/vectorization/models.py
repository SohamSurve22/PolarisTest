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


def clause_to_embeddable(clause: Clause) -> EmbeddableRecord:
  """Build an EmbeddableRecord from a document_pipeline Clause.

  Embeds a plain section-title + clause-text join. A richer retrieval_text
  rewrite can be swapped in here later without touching the embedding loop.
  """
  parts = []
  if clause.section_title:
    parts.append(clause.section_title.strip())
  parts.append(clause.clause_text.strip())
  retrieval_text = " — ".join(p for p in parts if p)

  return EmbeddableRecord(
    clause_id=clause.clause_id,
    document_id=clause.document_id,
    section_id=clause.section_id,
    section_title=clause.section_title,
    clause_number=clause.clause_number,
    clause_text=clause.clause_text,
    retrieval_text=retrieval_text,
    source=clause.model_dump(mode="json"),
  )
