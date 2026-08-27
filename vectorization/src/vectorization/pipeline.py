"""Loads document_pipeline output, embeds clauses, and stores them in pgvector."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from tqdm import tqdm

from document_pipeline.models.clause import SegmentedDocument
from semantic_graph.llm.ollama_client import OllamaLLMClient
from semantic_graph.retrieval_enrichment.llm_retrieval_summarizer import LLMRetrievalSummarizer
from semantic_graph.retrieval_enrichment.stage import RetrievalEnrichmentStage
from vectorization.config import VectorizationSettings, get_settings
from vectorization.embedder import OllamaEmbedder
from vectorization.models import clause_to_embeddable
from vectorization.store import VectorStore

logger = logging.getLogger(__name__)


def load_segmented_documents(clauses_dir: Path) -> list[SegmentedDocument]:
  """Load every SegmentedDocument JSON file produced by document_pipeline."""
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

  # Generate retrieval_text per clause via the local LLM before embedding.
  # This is a separate, cheaper-to-skip step: if it's turned off or the
  # local model isn't running, clause_to_embeddable() falls back to a
  # plain title+text join automatically.
  retrieval_summaries: dict = {}
  if settings.enable_retrieval_summarization:
    with OllamaLLMClient(model=settings.local_llm_model) as llm_client:
      stage = RetrievalEnrichmentStage(LLMRetrievalSummarizer(llm_client))
      for document in documents:
        act = document.metadata.extra.get("act") if document.metadata.extra else None
        summaries = stage.process(document.clauses, act=act)
        retrieval_summaries.update(summaries)
    logger.info("generated %d retrieval summaries", len(retrieval_summaries))

  records = [
    clause_to_embeddable(clause, retrieval_summaries)
    for document in documents
    for clause in document.clauses
  ]
  logger.info("prepared %d clauses for embedding", len(records))

  with OllamaEmbedder(settings) as embedder, VectorStore(settings) as store:
    batch_records = []
    batch_embeddings = []

    for record in tqdm(records, desc="embedding clauses"):
      embedding = embedder.embed(record.retrieval_text)
      batch_records.append(record)
      batch_embeddings.append(embedding)

      if len(batch_records) >= settings.batch_size:
        store.upsert_batch(batch_records, batch_embeddings)
        batch_records, batch_embeddings = [], []

    if batch_records:
      store.upsert_batch(batch_records, batch_embeddings)

  logger.info("done")
