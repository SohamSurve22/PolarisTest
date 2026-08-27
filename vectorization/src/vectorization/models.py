"""Bridge model between document_pipeline's Clause output and embedding storage.

The old vectorization.py assumed every input record already had a curated
``retrieval_text`` field (from a hand-built dataset). document_pipeline's
Clause model has no such field — it only has clause_text, section_title,
clause_number, etc. This module is the one place responsible for turning a
Clause into text worth embedding, so that logic doesn't get buried inside
the embedding loop.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from document_pipeline.models.clause import Clause
from semantic_graph.retrieval_enrichment.models import RetrievalSummary


class EmbeddableRecord(BaseModel):
  """A single unit of text to embed, plus the metadata to store alongside it."""

  clause_id: str
  document_id: str
  section_id: str
  section_title: str | None = None
  clause_number: str | None = None
  clause_text: str
  retrieval_text: str = Field(
    description="Text actually sent to the embedding model. Falls back to "
    "clause_text when no richer summary is available.",
  )
  source: dict = Field(
    default_factory=dict,
    description="Original clause payload, stored as-is in the `data` column "
    "for traceability and future re-embedding.",
  )


def clause_to_embeddable(
  clause: Clause,
  retrieval_summaries: dict[str, RetrievalSummary] | None = None,
) -> EmbeddableRecord:
  """Build an EmbeddableRecord from a document_pipeline Clause.

  Prefers the LLM-generated retrieval_text from
  semantic_graph.retrieval_enrichment when available (pass the mapping
  produced by RetrievalEnrichmentStage.process()). Falls back to a plain
  section-title + clause-text join for any clause not present in the
  mapping, or when no mapping is supplied at all.
  """
  summary = (retrieval_summaries or {}).get(clause.clause_id)
  if summary is not None:
    retrieval_text = summary.retrieval_text
  else:
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
