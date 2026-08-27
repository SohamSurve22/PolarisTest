-- Schema for legal_documents_vectorization.
-- Replaces the old mydb.sql, which was a raw data dump (rows of embeddings),
-- not a migration. This is the actual CREATE TABLE that should live in
-- version control; the data itself gets populated by `vectorization` at
-- run time, not committed to the repo.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS legal_documents_vectorization (
  clause_id    TEXT PRIMARY KEY,
  document_id  TEXT NOT NULL,
  section_id   TEXT NOT NULL,
  data         JSONB NOT NULL,
  -- Dimension must match VECTORIZATION_EMBEDDING_DIM / the embedding
  -- model in use (768 for nomic-embed-text).
  embedding    VECTOR(768) NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS legal_documents_vectorization_document_id_idx
  ON legal_documents_vectorization (document_id);

-- IVFFlat index for approximate nearest-neighbour search. Build this only
-- after the table has a meaningful amount of data (lists ~ sqrt(row_count)
-- is a reasonable starting point).
-- CREATE INDEX legal_documents_vectorization_embedding_idx
--   ON legal_documents_vectorization
--   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
