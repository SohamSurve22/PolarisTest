"""Abstract interface for all semantic graph stages.

Each stage takes an ``EntityDocument`` and the current ``GraphIR``, then
returns a new ``GraphIR`` with additional nodes and/or relationships.
Stages are chained by ``SemanticGraphBuilder`` using dependency injection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from document_pipeline.models.entity import EntityDocument

from graph_builder.graph_ir import GraphIR


class SemanticGraphStage(ABC):
    """Abstract interface for a single semantic graph construction stage.

    Every stage receives the original ``EntityDocument`` and the current
    ``GraphIR`` produced by the preceding stages, and returns a new or
    updated ``GraphIR``.

    Implementations must be deterministic, use no LLM, and generate no
    Cypher or Neo4j code.
    """

    @abstractmethod
    def process(
        self,
        document: EntityDocument,
        graph: GraphIR,
    ) -> GraphIR:
        """Process the document and update the graph IR.

        Args:
            document: The original entity-annotated document.
            graph: The current ``GraphIR`` from previous stages.

        Returns:
            Updated ``GraphIR`` with additional nodes/relationships.
        """
        ...
