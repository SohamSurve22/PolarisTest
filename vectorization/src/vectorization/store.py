"""Qdrant storage for embedded clauses."""

from __future__ import annotations

import logging
import math
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from vectorization.config import VectorizationSettings
from vectorization.models import EmbeddableRecord

logger = logging.getLogger(__name__)

# Stable namespace so the same (document_id, clause_id) always maps to the
# same Qdrant point id (UUID), making upserts idempotent.
_POINT_NAMESPACE = uuid.UUID("8c2e6d1a-4f3b-4a9e-9b0c-7d1e2f3a4b5c")


def point_id(document_id: str, clause_id: str) -> str:
  """Return a deterministic Qdrant point id for a clause."""
  return str(uuid.uuid5(_POINT_NAMESPACE, f"{document_id}:{clause_id}"))


def l2_normalize(vector: list[float]) -> list[float]:
  """Scale a vector to unit length. Zero vectors are returned unchanged."""
  norm = math.sqrt(sum(component * component for component in vector))
  if norm == 0.0:
    return vector
  return [component / norm for component in vector]


class VectorStore:
  """Owns the Qdrant client and batched upserts.

  Points are keyed by a UUID5 of (document_id, clause_id), so re-running after
  a partial failure or a document_pipeline re-export overwrites the same
  points instead of creating duplicates.
  """

  def __init__(
    self,
    settings: VectorizationSettings,
    client: QdrantClient | None = None,
  ) -> None:
    self._settings = settings
    self._client = client or QdrantClient(url=settings.qdrant_url)
    self._ensure_collection()

  def _ensure_collection(self) -> None:
    name = self._settings.qdrant_collection
    if self._client.collection_exists(name):
      return
    self._client.create_collection(
      collection_name=name,
      vectors_config=VectorParams(
        size=self._settings.embedding_dim,
        distance=Distance.COSINE,
      ),
    )

  def upsert_batch(
    self,
    records: list[EmbeddableRecord],
    embeddings: list[list[float]],
  ) -> None:
    """Insert or overwrite a batch of (record, embedding) points."""
    if len(records) != len(embeddings):
      raise ValueError("records and embeddings must be the same length")
    if not records:
      return

    dim = self._settings.embedding_dim
    points: list[PointStruct] = []
    for record, embedding in zip(records, embeddings, strict=True):
      if len(embedding) != dim:
        raise ValueError(
          f"embedding dimension {len(embedding)} does not match configured "
          f"dimension {dim}"
        )
      points.append(
        PointStruct(
          id=point_id(record.document_id, record.clause_id),
          vector=l2_normalize(embedding),
          payload={
            "source_type": "document_clause",
            "document_id": record.document_id,
            "clause_id": record.clause_id,
            "section_id": record.section_id,
            "section_title": record.section_title,
            "clause_number": record.clause_number,
            "clause_text": record.clause_text,
            "retrieval_text": record.retrieval_text,
            "embedding_model_version": self._settings.embedding_model,
            "language": "en",
            "law_code": None,
            "obligation_id": None,
          },
        )
      )
    self._client.upsert(
      collection_name=self._settings.qdrant_collection,
      points=points,
    )
    logger.info("upserted batch of %d points", len(points))

  def close(self) -> None:
    self._client.close()

  def __enter__(self) -> VectorStore:
    return self

  def __exit__(self, *exc_info: object) -> None:
    self.close()
