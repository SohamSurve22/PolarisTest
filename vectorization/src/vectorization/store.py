"""Postgres/pgvector storage for embedded clauses."""

from __future__ import annotations

import json
import logging

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extensions import connection as PGConnection

from vectorization.config import VectorizationSettings
from vectorization.models import EmbeddableRecord

logger = logging.getLogger(__name__)


class VectorStore:
  """Owns the Postgres connection and batched inserts.

  Unlike the old script (one connection, one giant loop, one commit at
  the very end), this commits per batch so a crash partway through only
  loses the current batch, not the whole run — and reruns are idempotent
  via ON CONFLICT on clause_id.
  """

  def __init__(self, settings: VectorizationSettings) -> None:
    self._settings = settings
    self._conn: PGConnection = psycopg2.connect(
      host=settings.pg_host,
      port=settings.pg_port,
      database=settings.pg_database,
      user=settings.pg_user,
      password=settings.pg_password,
    )
    register_vector(self._conn)

  def upsert_batch(
    self,
    records: list[EmbeddableRecord],
    embeddings: list[list[float]],
  ) -> None:
    """Insert or update a batch of (record, embedding) pairs in one transaction."""
    if len(records) != len(embeddings):
      raise ValueError("records and embeddings must be the same length")
    if not records:
      return

    table = self._settings.pg_table
    with self._conn.cursor() as cur:
      for record, embedding in zip(records, embeddings, strict=True):
        cur.execute(
          f"""
          INSERT INTO {table} (clause_id, document_id, section_id, data, embedding)
          VALUES (%s, %s, %s, %s, %s)
          ON CONFLICT (clause_id) DO UPDATE
            SET data = EXCLUDED.data, embedding = EXCLUDED.embedding
          """,
          (
            record.clause_id,
            record.document_id,
            record.section_id,
            json.dumps(record.source),
            embedding,
          ),
        )
    self._conn.commit()
    logger.info("committed batch of %d records", len(records))

  def close(self) -> None:
    self._conn.close()

  def __enter__(self) -> "VectorStore":
    return self

  def __exit__(self, *exc_info: object) -> None:
    self.close()
