"""Load merged statute JSON into EmbeddableRecord rows for dense RAG.

This path is separate from ``kg_obligation`` ingest so ``/analyze`` search
never mixes merged-corpus sections with catalog duties.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from vectorization.models import EmbeddableRecord

logger = logging.getLogger(__name__)


def load_rag_records(path: Path) -> list[EmbeddableRecord]:
  """Turn ``sections[]`` in a merged statute JSON file into rag_section records."""
  payload = json.loads(path.read_text(encoding="utf-8"))
  records: list[EmbeddableRecord] = []
  for section in payload.get("sections") or []:
    record = _section_to_record(section)
    if record is not None:
      records.append(record)
  logger.info("loaded %d rag_section records from %s", len(records), path)
  return records


def _section_to_record(section: dict[str, Any]) -> EmbeddableRecord | None:
  doc_id = str(section.get("doc_id") or "").strip()
  if not doc_id:
    return None
  retrieval = str(section.get("retrieval_text") or "").strip()
  clause = str(section.get("clause_text") or "").strip()
  text = retrieval or clause
  if not text:
    logger.info("skipping empty rag_section %s", doc_id)
    return None
  title = str(section.get("title") or "").strip()
  topics = list(section.get("topics") or [])
  act = str(section.get("act") or "").strip()
  return EmbeddableRecord(
    clause_id=doc_id,
    obligation_id=doc_id,
    section_id=doc_id,
    section_title=title or None,
    clause_text=clause or text,
    retrieval_text=text,
    source_type="rag_section",
    law_code=act or None,
    source={
      "chunk_index": 0,
      "chunk_type": "rag_section",
      "title": title,
      "topics": topics,
    },
  )
