"""Core abstractions and shared exceptions."""

from document_pipeline.core.base import BaseProcessor
from document_pipeline.core.exceptions import (
  CorruptedDocumentError,
  DocumentPipelineError,
  PipelineConfigurationError,
  PipelineStageError,
  UnreadableDocumentError,
  UnsupportedFileTypeError,
  ValidationError,
)

__all__ = [
  "BaseProcessor",
  "CorruptedDocumentError",
  "DocumentPipelineError",
  "PipelineConfigurationError",
  "PipelineStageError",
  "UnreadableDocumentError",
  "UnsupportedFileTypeError",
  "ValidationError",
]
