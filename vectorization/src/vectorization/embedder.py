"""Embedding backends: Ollama (default) and optional Sentence Transformers."""

from __future__ import annotations

import logging
from typing import Literal, Protocol

import httpx

from vectorization.config import VectorizationSettings

logger = logging.getLogger(__name__)

EmbedTask = Literal["document", "query"]
_ST_DEFAULT_MODEL = "all-mpnet-base-v2"


class EmbeddingError(RuntimeError):
  """Raised when the embedding backend fails for a given input."""


class EmbeddingProvider(Protocol):
  """Swap hatch for local embedding backends."""

  def embed(self, text: str, *, task: EmbedTask = "document") -> list[float]: ...

  def embed_batch(
    self,
    texts: list[str],
    *,
    task: EmbedTask = "document",
  ) -> list[list[float]]: ...

  def close(self) -> None: ...

  def __enter__(self) -> EmbeddingProvider: ...

  def __exit__(self, *exc_info: object) -> None: ...


class OllamaEmbedder:
  """Thin client around Ollama's /api/embeddings endpoint.

  nomic-embed-text expects task prefixes (``search_document:`` /
  ``search_query:``). Those are added here and never stored in Qdrant.
  """

  def __init__(self, settings: VectorizationSettings) -> None:
    self._settings = settings
    self._client = httpx.Client(timeout=settings.request_timeout_seconds)

  def embed(self, text: str, *, task: EmbedTask = "document") -> list[float]:
    """Return the embedding vector for a single piece of text."""
    prompt = _prefixed(text, task=task, settings=self._settings)
    try:
      response = self._client.post(
        self._settings.ollama_url,
        json={"model": self._settings.embedding_model, "prompt": prompt},
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
        "VECTORIZATION_EMBEDDING_DIM and the Qdrant collection vector size",
        len(embedding),
        self._settings.embedding_dim,
      )
    return embedding

  def embed_batch(
    self,
    texts: list[str],
    *,
    task: EmbedTask = "document",
  ) -> list[list[float]]:
    """Embed texts one HTTP call at a time, preserving order."""
    return [self.embed(text, task=task) for text in texts]

  def close(self) -> None:
    self._client.close()

  def __enter__(self) -> OllamaEmbedder:
    return self

  def __exit__(self, *exc_info: object) -> None:
    self.close()


class SentenceTransformersEmbedder:
  """Optional local Sentence Transformers backend. Not required for default ingest."""

  def __init__(self, settings: VectorizationSettings) -> None:
    self._settings = settings
    try:
      self._model = _load_sentence_transformer(settings.embedding_model)
    except ImportError as exc:
      raise EmbeddingError(
        "sentence-transformers extra is required for "
        "VECTORIZATION_EMBEDDING_BACKEND=sentence_transformers. "
        "Install with: pip install -e '.[st]'"
      ) from exc

  def embed(self, text: str, *, task: EmbedTask = "document") -> list[float]:
    return self.embed_batch([text], task=task)[0]

  def embed_batch(
    self,
    texts: list[str],
    *,
    task: EmbedTask = "document",
  ) -> list[list[float]]:
    del task
    if not texts:
      return []
    encoded = self._model.encode(
      texts,
      batch_size=self._settings.embed_batch_size,
      normalize_embeddings=False,
    )
    if hasattr(encoded, "tolist"):
      encoded = encoded.tolist()
    return [list(row) for row in encoded]

  def close(self) -> None:
    return None

  def __enter__(self) -> SentenceTransformersEmbedder:
    return self

  def __exit__(self, *exc_info: object) -> None:
    self.close()


def resolve_embedding_settings(settings: VectorizationSettings) -> VectorizationSettings:
  """Apply backend defaults so store payload model ids match the provider."""
  if settings.embedding_backend != "sentence_transformers":
    return settings
  if settings.embedding_model != "nomic-embed-text":
    return settings
  return settings.model_copy(update={"embedding_model": _ST_DEFAULT_MODEL})


def provider_from_settings(settings: VectorizationSettings) -> EmbeddingProvider:
  """Build the configured embedding backend."""
  resolved = resolve_embedding_settings(settings)
  backend = resolved.embedding_backend
  if backend == "ollama":
    return OllamaEmbedder(resolved)
  if backend == "sentence_transformers":
    return SentenceTransformersEmbedder(resolved)
  raise ValueError(f"unknown embedding backend: {backend}")


def _load_sentence_transformer(model_name: str) -> object:
  from sentence_transformers import SentenceTransformer

  return SentenceTransformer(model_name)


def _prefixed(text: str, *, task: EmbedTask, settings: VectorizationSettings) -> str:
  prefix = (
    settings.document_embed_prefix if task == "document" else settings.query_embed_prefix
  )
  if not prefix:
    return text
  if text.startswith(prefix):
    return text
  return f"{prefix}{text}"
