"""Coordinates execution of all pipeline stages in sequence."""

from document_pipeline.models.document import DocumentSource
from document_pipeline.models.semantic import SemanticExtractionInput
from document_pipeline.pipeline.stages.block_extractor import DocumentBlockExtractor
from document_pipeline.pipeline.stages.clause_builder import ClauseBuilder
from document_pipeline.pipeline.stages.clause_extractor import ClauseExtractor
from document_pipeline.pipeline.stages.cleaner import DocumentCleaner
from document_pipeline.pipeline.stages.llm_preparer import LLMPreparer
from document_pipeline.pipeline.stages.loader import DocumentLoader
from document_pipeline.pipeline.stages.section_extractor import SectionExtractor
from document_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


class DocumentPipelineOrchestrator:
  """Wires independent pipeline stages and executes them in order.

  Each stage is injected via constructor, preserving the Dependency
  Inversion Principle and enabling per-stage unit testing.
  """

  def __init__(
    self,
    loader: DocumentLoader,
    cleaner: DocumentCleaner,
    section_extractor: SectionExtractor,
    block_extractor: DocumentBlockExtractor,
    clause_builder: ClauseBuilder,
    clause_extractor: ClauseExtractor,
    llm_preparer: LLMPreparer,
  ) -> None:
    self._loader = loader
    self._cleaner = cleaner
    self._section_extractor = section_extractor
    self._block_extractor = block_extractor
    self._clause_builder = clause_builder
    self._clause_extractor = clause_extractor
    self._llm_preparer = llm_preparer

  def run(self, source: DocumentSource) -> SemanticExtractionInput:
    """Execute the full document intelligence pipeline.

    Args:
      source: Entry-point document reference.

    Returns:
      Semantic extraction input artifact for downstream analysis.

    Note:
      Processing logic is not yet implemented in individual stages.
    """
    logger.info("Starting pipeline for document: %s", source.metadata.document_id)

    loaded = self._loader.process(source)
    cleaned = self._cleaner.process(loaded)
    sectioned = self._section_extractor.process(cleaned)
    blocked = self._block_extractor.process(sectioned)
    candidate_doc = self._clause_builder.process(blocked)
    segmented = self._clause_extractor.process(candidate_doc)
    semantic_input = self._llm_preparer.process(segmented)

    logger.info("Pipeline complete for document: %s", source.metadata.document_id)
    return semantic_input
