"""Abstract interface for clause semantic analysis.

All clause analyzers implement the ``ClauseAnalyzer`` protocol so that
the enrichment stage can swap LLM providers (OpenAI, Groq, Ollama, etc.)
without changing any business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from semantic_graph.semantic_enrichment.enrichment_models import ClauseMeaning


class ClauseAnalyzer(ABC):
    """Abstract base for clause semantic analyzers.

    Subclasses must implement ``analyze`` to return a ``ClauseMeaning``
    for the given clause text and identifier.
    """

    @abstractmethod
    def analyze(self, clause_text: str, clause_id: str) -> ClauseMeaning:
        """Extract semantic meaning from a single clause.

        Args:
            clause_text: The raw text of the legal clause.
            clause_id:   Stable identifier for the source clause.

        Returns:
            A ``ClauseMeaning`` with zero or more extracted ``Obligation``
            objects.
        """
        ...
