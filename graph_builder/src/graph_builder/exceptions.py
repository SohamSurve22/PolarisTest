"""Custom exceptions for the graph builder pipeline."""


class GraphBuilderError(Exception):
  """Base exception for all graph builder errors."""


class GraphValidationError(GraphBuilderError):
  """Raised when graph IR fails validation."""


class LLMGraphBuilderError(GraphBuilderError):
  """Raised when the LLM graph builder fails to produce valid output."""


class CypherGenerationError(GraphBuilderError):
  """Raised when Cypher generation fails."""


class Neo4jLoaderError(GraphBuilderError):
  """Raised when Neo4j connection or execution fails."""
