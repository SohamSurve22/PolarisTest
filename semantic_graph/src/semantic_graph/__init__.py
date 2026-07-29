"""Semantic Graph Builder for PolarisLex.

Converts ``EntityDocument`` (output of the entity extraction pipeline) into a
``GraphIR`` intermediate representation.  The first stage builds the document
hierarchy skeleton; the second stage resolves cross-references.  Future
stages will add definitions, obligations, and ontology mappings.
"""

from semantic_graph.hierarchy_builder import HierarchyBuilder
from semantic_graph.reference_resolver import ReferenceResolver
from semantic_graph.semantic_graph_builder import SemanticGraphBuilder
from semantic_graph.semantic_graph_stage import SemanticGraphStage

__all__ = [
    "HierarchyBuilder",
    "ReferenceResolver",
    "SemanticGraphBuilder",
    "SemanticGraphStage",
]
