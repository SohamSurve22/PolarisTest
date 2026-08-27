"""Data model for retrieval-text generation.

Mirrors the shape of semantic_enrichment/enrichment_models.py, but for a
different kind of enrichment: a plain-English, self-contained rewrite of
a clause meant to be embedded and searched — not the obligations it imposes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievalSummary:
  """A retrieval-optimised rewrite of a single clause.

  Attributes:
      clause_id:      Stable identifier of the source clause.
      retrieval_text: Self-contained, plain-English rewrite of the clause —
                       spells out which act/section it's from and resolves
                       pronouns/cross-references, so it reads well as a
                       standalone search result and embeds well on its own.
  """

  clause_id: str = ""
  retrieval_text: str = ""
