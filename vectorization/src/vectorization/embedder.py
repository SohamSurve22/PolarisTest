"""Embedding client for the local Ollama model."""

from __future__ import annotations

import logging

import httpx

from vectorization.config import VectorizationSettings

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
  """Raised when the embedding backend fails for a given input."""


class OllamaEmbedder:
  """Thin client around Ollama's /api/embeddings endpoint.

  Kept as its own class (rather than a bare requests.post call) so the
  backend can be swapped later without touching pipeline.py.
  """

  def __init__(self, settings: VectorizationSettings) -> None:
    self._settings = settings
    self._client = httpx.Client(timeout=settings.request_timeout_seconds)

  def embed(self, text: str) -> list[float]:
    """Return the embedding vector for a single piece of text."""
    try:
      response = self._client.post(
        self._settings.ollama_url,
        json={"model": self._settings.embedding_model, "prompt": text},
      )
      response.raise_for_status()
    except httpx.HTTPError as exc:
      raise EmbeddingError(f"embedding request failed: {exc}") from exc

    payload = response.json()
    embedding = payload.get("embedding")
    if not embedding:
      raise EmbeddingError(f"no embedding in response: {payload}")

    if len(embedding) != self._settings.embedding_dim:
      logger.warning(
        "embedding dim %d does not match configured dim %d — check "
        "VECTORIZATION_EMBEDDING_DIM and the pgvector column definition",
        len(embedding),
        self._settings.embedding_dim,
      )
    return embedding

  def close(self) -> None:
    self._client.close()

  def __enter__(self) -> "OllamaEmbedder":
    return self

  def __exit__(self, *exc_info: object) -> None:
    self.close()
