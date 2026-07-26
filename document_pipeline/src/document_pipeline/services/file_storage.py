"""Abstract file storage service for document source access."""

from abc import ABC, abstractmethod
from pathlib import Path


class FileStorageService(ABC):
  """Abstraction over document file storage.

  Concrete implementations may read from local disk, object storage,
  or other backends in a future iteration.
  """

  @abstractmethod
  def resolve_path(self, document_id: str) -> Path:
    """Resolve the filesystem path for a given document identifier."""

  @abstractmethod
  def exists(self, document_id: str) -> bool:
    """Return whether the document exists in storage."""

  @abstractmethod
  def read_bytes(self, document_id: str) -> bytes:
    """Read the raw bytes of a stored document."""
