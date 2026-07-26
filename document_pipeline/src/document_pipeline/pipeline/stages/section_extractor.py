"""Stage 3: Section Extraction."""

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.document import CleanedDocument
from document_pipeline.models.section import SectionedDocument
from document_pipeline.sectioning.heading_detector import HeadingDetector
from document_pipeline.sectioning.section_assembler import SectionAssembler


class SectionExtractor(BaseProcessor[CleanedDocument, SectionedDocument]):
  """Identifies and extracts structural sections within a cleaned legal document.

  Heading detection and section assembly are delegated to dedicated components.
  No clause extraction or semantic analysis is performed at this stage.
  """

  def __init__(
    self,
    heading_detector: HeadingDetector | None = None,
    section_assembler: SectionAssembler | None = None,
  ) -> None:
    self._heading_detector = heading_detector or HeadingDetector()
    self._section_assembler = section_assembler or SectionAssembler()

  def process(self, input_data: CleanedDocument) -> SectionedDocument:
    """Extract and partition document sections."""
    full_text = input_data.cleaned_text
    headings = self._heading_detector.detect(full_text)
    sections = self._section_assembler.assemble(full_text, headings)

    return SectionedDocument(
      metadata=input_data.metadata,
      full_text=full_text,
      sections=sections,
    )
