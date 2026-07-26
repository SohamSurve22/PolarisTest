"""Stage 2: Document Cleaning."""

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.document import CleanedDocument, LoadedDocument
from document_pipeline.utils.text_normalization import normalize_document_text


class DocumentCleaner(BaseProcessor[LoadedDocument, CleanedDocument]):
  """Normalizes and cleans raw document text for structural analysis.

  Applies deterministic whitespace and Unicode normalization only. No
  rewriting, structural inference, or semantic analysis is performed.
  """

  def process(self, input_data: LoadedDocument) -> CleanedDocument:
    """Clean and normalize a loaded document."""
    cleaned_text, cleaning_notes = normalize_document_text(input_data.raw_text)

    return CleanedDocument(
      metadata=input_data.metadata,
      cleaned_text=cleaned_text,
      cleaning_notes=cleaning_notes,
    )
