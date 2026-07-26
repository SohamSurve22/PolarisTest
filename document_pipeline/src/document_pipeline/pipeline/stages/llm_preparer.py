"""Abstract interface for Stage 5: LLM Preparation."""

from abc import abstractmethod

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.clause import SegmentedDocument
from document_pipeline.models.semantic import SemanticExtractionInput


class LLMPreparer(BaseProcessor[SegmentedDocument, SemanticExtractionInput]):
  """Prepares segmented clauses into chunks for downstream semantic extraction.

  This stage structures text for semantic analysis without performing
  any LLM calls itself.
  """

  @abstractmethod
  def process(self, input_data: SegmentedDocument) -> SemanticExtractionInput:
    """Prepare document clauses for semantic extraction."""
