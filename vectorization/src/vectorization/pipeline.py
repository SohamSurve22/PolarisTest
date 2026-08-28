"""Loads document_pipeline output, embeds clauses, and stores them in Qdrant."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from tqdm import tqdm

from vectorization.chunking import sources_to_embeddable
from vectorization.config import VectorizationSettings, get_settings
from vectorization.embedder import provider_from_settings, resolve_embedding_settings
from vectorization.kg import load_kg_records
from vectorization.models import EmbeddableRecord, SearchHit
from vectorization.sources import load_embeddable_sources
from vectorization.store import VectorStore

logger = logging.getLogger(__name__)


def load_segmented_documents(clauses_dir: Path) -> list[SegmentedDocument]:
  """Load every document_pipeline JSON file that is a SegmentedDocument."""
  from document_pipeline.models.clause import SegmentedDocument

  documents = []
  for path in sorted(clauses_dir.glob("DOC_*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("entity_clauses") or payload.get("contextual_clauses"):
      continue
    documents.append(SegmentedDocument.model_validate(payload))
  logger.info("loaded %d documents from %s", len(documents), clauses_dir)
  return documents


def run(settings: VectorizationSettings | None = None) -> None:
  """Entry point: embed every clause from document_pipeline's output."""
  settings = settings or get_settings()
  clauses_dir = Path(settings.clauses_dir)

  documents = load_embeddable_sources(clauses_dir)
  skipped = 0
  records = []
  for source in documents:
    converted = sources_to_embeddable(
      [source],
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
  _embed_and_upsert(records, settings, desc="embedding clauses")
  logger.info("done")


def run_kg(settings: VectorizationSettings | None = None) -> None:
  """Embed KG obligation and section JSON into the same Qdrant collection."""
  settings = settings or get_settings()
  kg_dir = Path(settings.kg_dir)
  records = load_kg_records(
    kg_dir,
    max_tokens=settings.kg_max_tokens,
    overlap_tokens=settings.chunk_overlap_tokens,
  )
  logger.info("prepared %d KG records from %s", len(records), kg_dir)
  _embed_and_upsert(records, settings, desc="embedding kg")
  logger.info("done")


def reembed(settings: VectorizationSettings | None = None) -> None:
  """Rebuild Qdrant points under the current embedding model.

  KG obligations/sections are re-upserted first, then document clauses, so
  clause-to-law search stays in one vector space. Does not delete the
  collection or touch stored reports.
  """
  settings = settings or get_settings()
  run_kg(settings)
  run(settings)


def _embed_and_upsert(
  records: list[EmbeddableRecord],
  settings: VectorizationSettings,
  *,
  desc: str,
) -> None:
  settings = resolve_embedding_settings(settings)
  texts = [record.retrieval_text for record in records]
  with provider_from_settings(settings) as embedder, VectorStore(settings) as store:
    all_embeddings: list[list[float]] = []
    for start in tqdm(
      range(0, len(texts), settings.embed_batch_size),
      desc=desc,
    ):
      batch_texts = texts[start : start + settings.embed_batch_size]
      all_embeddings.extend(embedder.embed_batch(batch_texts, task="document"))

    for start in range(0, len(records), settings.batch_size):
      store.upsert_batch(
        records[start : start + settings.batch_size],
        all_embeddings[start : start + settings.batch_size],
      )


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
