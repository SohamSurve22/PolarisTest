"""Offline knowledge graph ingestion pipeline for PolarisLex.

Converts structured legal document output (``EntityDocument``) into a
validated Neo4j knowledge graph.  This module never makes compliance
decisions — it only builds the graph.
"""

from graph_builder.cypher_generator import CypherGenerator, CypherStatement
from graph_builder.exceptions import (
  CypherGenerationError,
  GraphBuilderError,
  GraphValidationError,
  LLMGraphBuilderError,
  Neo4jLoaderError,
)
from graph_builder.graph_builder_pipeline import GraphBuilderPipeline, GraphBuildStats
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship
from graph_builder.graph_validator import GraphValidator
from graph_builder.kg_export import graph_ir_to_kg_dict, write_kg_export
from graph_builder.llm_graph_builder import LLMGraphBuilder
from graph_builder.mapping_failures import MappingFailure
from graph_builder.neo4j_loader import Neo4jConfig, Neo4jLoader
from graph_builder.openie import OpenIEExtractor
from graph_builder.policy_graph_builder import PolicyGraphBuilder
from graph_builder.propositions import RawProposition

__all__ = [
  "CypherGenerationError",
  "CypherGenerator",
  "CypherStatement",
  "GraphBuildStats",
  "GraphBuilderError",
  "GraphBuilderPipeline",
  "GraphIR",
  "GraphNode",
  "GraphRelationship",
  "GraphValidationError",
  "GraphValidator",
  "LLMGraphBuilder",
  "LLMGraphBuilderError",
  "MappingFailure",
  "Neo4jConfig",
  "Neo4jLoader",
  "Neo4jLoaderError",
  "OpenIEExtractor",
  "PolicyGraphBuilder",
  "RawProposition",
  "graph_ir_to_kg_dict",
  "write_kg_export",
]
