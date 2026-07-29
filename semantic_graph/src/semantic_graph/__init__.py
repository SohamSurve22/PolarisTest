"""Semantic Graph Builder for PolarisLex.

Converts ``EntityDocument`` (output of the entity extraction pipeline) into a
``GraphIR`` intermediate representation.  The first stage builds the document
hierarchy skeleton; the second stage resolves cross-references.  Additional
stages add semantic enrichment via LLM-based clause analysis.
"""

from semantic_graph.hierarchy_builder import HierarchyBuilder
from semantic_graph.reference_resolver import ReferenceResolver
from semantic_graph.semantic_enrichment.clause_analyzer import ClauseAnalyzer
from semantic_graph.semantic_enrichment.enrichment_models import ClauseMeaning, Obligation
from semantic_graph.semantic_enrichment.llm_clause_analyzer import LLMClauseAnalyzer, LLMClient
from semantic_graph.semantic_enrichment.semantic_enrichment_stage import SemanticEnrichmentStage
from semantic_graph.semantic_graph_builder import SemanticGraphBuilder
from semantic_graph.semantic_graph_stage import SemanticGraphStage

__all__ = [
    "ClauseAnalyzer",
    "ClauseMeaning",
    "HierarchyBuilder",
    "LLMClauseAnalyzer",
    "LLMClient",
    "Obligation",
    "ReferenceResolver",
    "SemanticGraphBuilder",
    "SemanticGraphStage",
    "SemanticEnrichmentStage",
]
