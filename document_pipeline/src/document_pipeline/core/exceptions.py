"""Custom exceptions for the document intelligence pipeline."""


class DocumentPipelineError(Exception):
  """Base exception for all pipeline-related errors."""


class PipelineConfigurationError(DocumentPipelineError):
  """Raised when pipeline configuration is invalid or incomplete."""


class PipelineStageError(DocumentPipelineError):
  """Raised when a specific pipeline stage fails during processing."""

  def __init__(self, stage_name: str, message: str) -> None:
    self.stage_name = stage_name
    super().__init__(f"[{stage_name}] {message}")


class ValidationError(DocumentPipelineError):
  """Raised when input or output data fails validation."""


class UnsupportedFileTypeError(DocumentPipelineError):
  """Raised when a document format is not supported by the loader."""


class UnreadableDocumentError(DocumentPipelineError):
  """Raised when a document cannot be read from its source."""


class CorruptedDocumentError(DocumentPipelineError):
  """Raised when a document file is present but structurally invalid."""
