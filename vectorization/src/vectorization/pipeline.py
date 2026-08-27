"""Loads document_pipeline output, embeds clauses, and stores them in Qdrant."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from tqdm import tqdm

from document_pipeline.models.clause import SegmentedDocument
from vectorization.chunking import clauses_to_embeddable
from vectorization.config import VectorizationSettings, get_settings
from vectorization.embedder import provider_from_settings, resolve_embedding_settings
from vectorization.models import SearchHit
from vectorization.store import VectorStore

logger = logging.getLogger(__name__)


def load_segmented_documents(clauses_dir: Path) -> list[SegmentedDocument]:
  """Load every document_pipeline JSON file (preview artifacts with clauses)."""
  documents = []
  for path in sorted(clauses_dir.glob("DOC_*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents.append(SegmentedDocument.model_validate(payload))
  logger.info("loaded %d documents from %s", len(documents), clauses_dir)
  return documents


def run(settings: VectorizationSettings | None = None) -> None:
  """Entry point: embed every clause from document_pipeline's output."""
  settings = settings or get_settings()
  clauses_dir = Path(settings.clauses_dir)

  documents = load_segmented_documents(clauses_dir)
  skipped = 0
  records = []
  for document in documents:
    for clause in document.clauses:
      converted = clauses_to_embeddable(
        [clause],
        min_tokens=settings.min_clause_tokens,
        max_tokens=settings.max_clause_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
      )
      if not converted:
        skipped += 1
      records.extend(converted)
  logger.info(
    "prepared %d records for embedding (%d short clauses skipped)",
    len(records),
    skipped,
  )

  settings = resolve_embedding_settings(settings)
  texts = [record.retrieval_text for record in records]

  with provider_from_settings(settings) as embedder, VectorStore(settings) as store:
    all_embeddings: list[list[float]] = []
    for start in tqdm(
      range(0, len(texts), settings.embed_batch_size),
      desc="embedding clauses",
    ):
      batch_texts = texts[start : start + settings.embed_batch_size]
      all_embeddings.extend(embedder.embed_batch(batch_texts, task="document"))

    for start in range(0, len(records), settings.batch_size):
      store.upsert_batch(
        records[start : start + settings.batch_size],
        all_embeddings[start : start + settings.batch_size],
      )

  logger.info("done")


def search_text(
  query: str,
  settings: VectorizationSettings | None = None,
  *,
  top_k: int | None = None,
  min_score: float | None = None,
  source_type: str = "document_clause",
  document_id: str | None = None,
) -> list[SearchHit]:
  """Embed query text and return kNN hits from Qdrant."""
  settings = resolve_embedding_settings(settings or get_settings())
  with provider_from_settings(settings) as embedder, VectorStore(settings) as store:
    vector = embedder.embed(query, task="query")
    return store.search(
      vector,
      top_k=top_k if top_k is not None else settings.search_top_k,
      min_score=min_score if min_score is not None else settings.search_min_score,
      source_type=source_type,
      document_id=document_id,
    )
