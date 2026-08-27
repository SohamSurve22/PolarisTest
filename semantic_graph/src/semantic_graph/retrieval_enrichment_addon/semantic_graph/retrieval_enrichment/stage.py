"""Retrieval enrichment stage — generates retrieval_text for every clause.

Unlike SemanticEnrichmentStage (which enriches a GraphIR after graph
construction), this operates directly on document_pipeline's Clause
objects, because retrieval_text is needed by `vectorization` upstream of
graph building, not downstream of it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from semantic_graph.retrieval_enrichment.models import RetrievalSummary
from semantic_graph.retrieval_enrichment.summarizer import RetrievalSummarizer

if TYPE_CHECKING:
  from collections.abc import Iterable

  from document_pipeline.models.clause import Clause


class RetrievalEnrichmentStage:
  """Generates a RetrievalSummary for every clause in a document.

  Args:
      summarizer: The ``RetrievalSummarizer`` to use for generation.
  """

  def __init__(self, summarizer: RetrievalSummarizer) -> None:
    self._summarizer = summarizer

  def process(
    self,
    clauses: Iterable[Clause],
    *,
    act: str | None = None,
  ) -> dict[str, RetrievalSummary]:
    """Generate retrieval_text for each clause.

    Args:
        clauses: Clauses to summarize (from a SegmentedDocument).
        act:     Name of the source act, if known — passed through to
                 give the model context it can't infer from clause text
                 alone.

    Returns:
        A mapping of clause_id -> RetrievalSummary. Clauses that fail to
        summarize are skipped, not raised — callers (e.g. vectorization)
        should fall back to clause_text for any clause_id missing here.
    """
    summaries: dict[str, RetrievalSummary] = {}
    for clause in clauses:
      text = clause.clause_text.strip()
      if not text:
        continue
      summary = self._summarizer.summarize(
        text,
        clause.clause_id,
        act=act,
        section_label=clause.clause_number,
      )
      summaries[clause.clause_id] = summary
    return summaries
