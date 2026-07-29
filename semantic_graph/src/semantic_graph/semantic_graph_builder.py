"""Orchestrator for the Semantic Graph pipeline.

Pipeline:
    EntityDocument
        ↓  HierarchyBuilder
        ↓  ReferenceResolver
        ↓  (future stages)
    GraphIR

New stages plug in via dependency injection without modifying this class.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from semantic_graph.hierarchy_builder import HierarchyBuilder
from semantic_graph.reference_resolver import ReferenceResolver

if TYPE_CHECKING:
    from document_pipeline.models.entity import EntityDocument

from graph_builder.graph_ir import GraphIR


class SemanticGraphBuilder:
    """Orchestrates the conversion of an ``EntityDocument`` to ``GraphIR``.

    Uses dependency injection so future stages can be plugged into the
    pipeline without modifying this class.

    Active stages (in order):
        1. ``HierarchyBuilder`` — constructs the document skeleton.
        2. ``ReferenceResolver`` — resolves cross-references.
    """

    def __init__(
        self,
        hierarchy_builder: HierarchyBuilder | None = None,
        reference_resolver: ReferenceResolver | None = None,
    ) -> None:
        """Initialize the semantic graph builder.

        Args:
            hierarchy_builder: Injected hierarchy builder.  Defaults to a
                fresh ``HierarchyBuilder`` if not provided.
            reference_resolver: Injected reference resolver.  Defaults to a
                fresh ``ReferenceResolver`` if not provided.
        """
        self._hierarchy_builder = hierarchy_builder or HierarchyBuilder()
        self._reference_resolver = reference_resolver or ReferenceResolver()

    def build(self, document: EntityDocument) -> GraphIR:
        """Run all active stages and return the combined ``GraphIR``.

        Args:
            document: The entity-annotated document to convert.

        Returns:
            Combined ``GraphIR`` from all active stages.
        """
        ir = self._hierarchy_builder.build(document)
        ir = self._reference_resolver.process(document, ir)
        return ir
