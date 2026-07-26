"""Coordinates execution of all pipeline stages in sequence."""

from dataclasses import dataclass

from document_pipeline.models.document import CleanedDocument, DocumentSource, LoadedDocument
from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.semantic import ClassifiedDocument, SemanticExtractionInput
from document_pipeline.models.clause import SegmentedDocument
from document_pipeline.models.context import ContextDocument
from document_pipeline.models.section import SectionedDocument
from document_pipeline.pipeline.stages.block_extractor import DocumentBlockExtractor
from document_pipeline.pipeline.stages.clause_builder import ClauseBuilder
from document_pipeline.pipeline.stages.clause_extractor import ClauseExtractor
from document_pipeline.pipeline.stages.cleaner import DocumentCleaner
from document_pipeline.pipeline.stages.context_builder import ContextBuilder
from document_pipeline.pipeline.stages.document_understanding import DocumentUnderstanding
from document_pipeline.pipeline.stages.entity_extractor import EntityExtractor
from document_pipeline.pipeline.stages.llm_preparer import DefaultLLMPreparer, LLMPreparer
from document_pipeline.pipeline.stages.loader import DocumentLoader
from document_pipeline.pipeline.stages.section_extractor import SectionExtractor
from document_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineOutputs:
  """Artifacts produced by each stage of a full pipeline run."""

  loaded: LoadedDocument
  cleaned: CleanedDocument
  sectioned: SectionedDocument
  segmented: SegmentedDocument
  classified: ClassifiedDocument
  context: ContextDocument
  entity: EntityDocument
  semantic: SemanticExtractionInput


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
    document_understanding: DocumentUnderstanding,
    context_builder: ContextBuilder,
    entity_extractor: EntityExtractor,
    llm_preparer: LLMPreparer,
  ) -> None:
    self._loader = loader
    self._cleaner = cleaner
    self._section_extractor = section_extractor
    self._block_extractor = block_extractor
    self._clause_builder = clause_builder
    self._clause_extractor = clause_extractor
    self._document_understanding = document_understanding
    self._context_builder = context_builder
    self._entity_extractor = entity_extractor
    self._llm_preparer = llm_preparer

  def run(self, source: DocumentSource) -> PipelineOutputs:
    """Execute the full document intelligence pipeline.

    Args:
      source: Entry-point document reference.

    Returns:
      Artifacts from every pipeline stage, including final semantic input.
    """
    logger.info("Starting pipeline for document: %s", source.metadata.document_id)

    loaded = self._loader.process(source)
    cleaned = self._cleaner.process(loaded)
    sectioned = self._section_extractor.process(cleaned)
    blocked = self._block_extractor.process(sectioned)
    candidate_doc = self._clause_builder.process(blocked)
    segmented = self._clause_extractor.process(candidate_doc)
    classified = self._document_understanding.process(segmented)
    context = self._context_builder.process(classified)
    entity = self._entity_extractor.process(context)
    semantic = self._llm_preparer.process(entity)

    logger.info("Pipeline complete for document: %s", source.metadata.document_id)
    return PipelineOutputs(
      loaded=loaded,
      cleaned=cleaned,
      sectioned=sectioned,
      segmented=segmented,
      classified=classified,
      context=context,
      entity=entity,
      semantic=semantic,
    )


def create_default_orchestrator() -> DocumentPipelineOrchestrator:
  """Construct an orchestrator with default implementations for every stage."""
  return DocumentPipelineOrchestrator(
    loader=DocumentLoader(),
    cleaner=DocumentCleaner(),
    section_extractor=SectionExtractor(),
    block_extractor=DocumentBlockExtractor(),
    clause_builder=ClauseBuilder(),
    clause_extractor=ClauseExtractor(),
    document_understanding=DocumentUnderstanding(),
    context_builder=ContextBuilder(),
    entity_extractor=EntityExtractor(),
    llm_preparer=DefaultLLMPreparer(),
  )
