"""Abstract interface for retrieval-text generation.

Mirrors semantic_enrichment/clause_analyzer.py's ClauseAnalyzer pattern,
so provider swaps and testing work the same way for both enrichment types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from semantic_graph.retrieval_enrichment.models import RetrievalSummary


class RetrievalSummarizer(ABC):
  """Abstract base for retrieval-text generators.

  Subclasses must implement ``summarize`` to return a ``RetrievalSummary``
  for the given clause text, act, and section context.
  """

  @abstractmethod
  def summarize(
    self,
    clause_text: str,
    clause_id: str,
    *,
    act: str | None = None,
    section_label: str | None = None,
  ) -> RetrievalSummary:
    """Generate a retrieval-optimised rewrite of a single clause.

    Args:
        clause_text:   The raw text of the legal clause.
        clause_id:     Stable identifier for the source clause.
        act:           Name of the act/regulation this clause belongs to,
                        if known (e.g. "SPDI_RULES_2011"). Included so the
                        model can name it explicitly in the rewrite.
        section_label: Section/subsection label, if known (e.g. "5(1)").

    Returns:
        A ``RetrievalSummary`` with the generated retrieval_text.
    """
    ...
