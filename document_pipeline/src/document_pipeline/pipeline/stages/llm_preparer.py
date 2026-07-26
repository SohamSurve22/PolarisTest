"""LLM preparation stage — structures enriched clauses for semantic extraction."""

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.semantic import LLMChunk, SemanticExtractionInput


class LLMPreparer(BaseProcessor[EntityDocument, SemanticExtractionInput]):
  """Prepares entity-enriched clauses into chunks for downstream semantic extraction.

  This stage structures text for semantic analysis without performing
  any LLM calls itself.
  """

  def process(self, input_data: EntityDocument) -> SemanticExtractionInput:
    """Prepare document clauses for semantic extraction."""


class DefaultLLMPreparer(LLMPreparer):
  """Builds one LLM chunk per entity clause with structural context metadata."""

  def process(self, input_data: EntityDocument) -> SemanticExtractionInput:
    chunks: list[LLMChunk] = []

    for entity_clause in input_data.entity_clauses:
      contextual = entity_clause.contextual_clause
      classified = contextual.classified_clause
      clause = classified.clause
      text = clause.clause_text.strip()
      if not text:
        continue

      context: dict[str, str] = {
        "role": classified.role.value,
        "section_id": clause.section_id,
        "confidence": str(classified.confidence),
      }

      if classified.classification_reason:
        context["classification_reason"] = ",".join(classified.classification_reason)

      if entity_clause.entities:
        context["entities"] = ",".join(
          entity.entity_text for entity in entity_clause.entities[:8]
        )

      if contextual.detected_references:
        context["references"] = ",".join(
          reference.reference_text for reference in contextual.detected_references[:8]
        )

      chunks.append(
        LLMChunk(
          chunk_id=clause.clause_id,
          clause_id=clause.clause_id,
          text=text,
          token_estimate=max(1, len(text) // 4),
          context=context,
        ),
      )

    return SemanticExtractionInput(metadata=input_data.metadata, chunks=chunks)
