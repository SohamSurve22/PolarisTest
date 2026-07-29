"""Graph builder pipeline orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from graph_builder.cypher_generator import CypherGenerator, CypherStatement
from graph_builder.graph_ir import GraphIR
from graph_builder.graph_validator import GraphValidator
from graph_builder.llm_graph_builder import LLMGraphBuilder
from graph_builder.neo4j_loader import Neo4jLoader

if TYPE_CHECKING:
  from document_pipeline.models.entity import EntityDocument


@dataclass
class GraphBuildStats:
  """Statistics returned after a successful graph build."""

  nodes_created: int = 0
  relationships_created: int = 0
  execution_time_ms: float = 0.0
  validation_warnings: list[str] = field(default_factory=list)
  nodes_in_ir: int = 0
  relationships_in_ir: int = 0


class GraphBuilderPipeline:
  """Orchestrates EntityDocument → GraphIR → Neo4j ingestion."""

  def __init__(
    self,
    llm_builder: LLMGraphBuilder,
    validator: GraphValidator | None = None,
    cypher_generator: CypherGenerator | None = None,
    neo4j_loader: Neo4jLoader | None = None,
  ) -> None:
    """Initialize the pipeline with injectable stage implementations.

    Args:
      llm_builder: Converts ``EntityDocument`` into graph IR.
      validator: Validates graph IR. Defaults to ``GraphValidator``.
      cypher_generator: Generates Cypher. Defaults to ``CypherGenerator``.
      neo4j_loader: Loads Cypher into Neo4j. Optional — skip load if ``None``.
    """
    self._llm_builder = llm_builder
    self._validator = validator or GraphValidator()
    self._cypher_generator = cypher_generator or CypherGenerator()
    self._neo4j_loader = neo4j_loader

  def build(self, entity_document: EntityDocument) -> GraphBuildStats:
    """Run the full graph build pipeline.

    Args:
      entity_document: Structured output from the semantic pipeline.

    Returns:
      Build statistics including node/relationship counts and timing.
    """
    start = time.perf_counter()

    graph_ir = self._llm_builder.build(entity_document)
    warnings = self._validator.validate(graph_ir)
    statements = self._cypher_generator.generate(graph_ir)

    nodes_created = 0
    relationships_created = 0

    if self._neo4j_loader is not None:
      self._neo4j_loader.connect()
      try:
        load_stats = self._neo4j_loader.execute(statements)
        nodes_created = load_stats["nodes_created"]
        relationships_created = load_stats["relationships_created"]
      finally:
        self._neo4j_loader.close()

    elapsed_ms = (time.perf_counter() - start) * 1000

    return GraphBuildStats(
      nodes_created=nodes_created,
      relationships_created=relationships_created,
      execution_time_ms=elapsed_ms,
      validation_warnings=warnings,
      nodes_in_ir=len(graph_ir.nodes),
      relationships_in_ir=len(graph_ir.relationships),
    )

  def build_from_ir(self, graph_ir: GraphIR) -> GraphBuildStats:
    """Run validation, Cypher generation, and Neo4j load from pre-built IR.

    Skips the LLM stage — useful for testing and replay.

    Args:
      graph_ir: Pre-built graph intermediate representation.

    Returns:
      Build statistics including node/relationship counts and timing.
    """
    start = time.perf_counter()

    warnings = self._validator.validate(graph_ir)
    statements = self._cypher_generator.generate(graph_ir)

    nodes_created = 0
    relationships_created = 0

    if self._neo4j_loader is not None:
      self._neo4j_loader.connect()
      try:
        load_stats = self._neo4j_loader.execute(statements)
        nodes_created = load_stats["nodes_created"]
        relationships_created = load_stats["relationships_created"]
      finally:
        self._neo4j_loader.close()

    elapsed_ms = (time.perf_counter() - start) * 1000

    return GraphBuildStats(
      nodes_created=nodes_created,
      relationships_created=relationships_created,
      execution_time_ms=elapsed_ms,
      validation_warnings=warnings,
      nodes_in_ir=len(graph_ir.nodes),
      relationships_in_ir=len(graph_ir.relationships),
    )

  def generate_cypher(self, graph_ir: GraphIR) -> list[CypherStatement]:
    """Validate IR and return Cypher statements without loading Neo4j.

    Args:
      graph_ir: Graph intermediate representation.

    Returns:
      Parameterized Cypher statements after validation.
    """
    self._validator.validate(graph_ir)
    return self._cypher_generator.generate(graph_ir)
