"""Load KG JSON files into EmbeddableRecord rows for Qdrant."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from vectorization.chunking import split_text, token_count
from vectorization.kg_models import KgFile
from vectorization.models import EmbeddableRecord

logger = logging.getLogger(__name__)


def kg_file_to_records(
  payload: dict[str, Any] | KgFile,
  *,
  max_tokens: int,
  overlap_tokens: int,
) -> list[EmbeddableRecord]:
  """Turn one law JSON object into embeddable KG chunks."""
  kg_file = payload if isinstance(payload, KgFile) else KgFile.model_validate(payload)
  records: list[EmbeddableRecord] = []
  for section in kg_file.sections:
    records.extend(
      _item_to_records(
        law_code=kg_file.law_code,
        language=kg_file.language,
        source_type="kg_section",
        chunk_type="section_text",
        text=section.text,
        section_id=section.section_id,
        section_title=section.title,
        obligation_id=None,
        item_id=section.section_id,
        prefix_title=True,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
      )
    )
  for obligation in kg_file.obligations:
    records.extend(
      _item_to_records(
        law_code=kg_file.law_code,
        language=kg_file.language,
        source_type="kg_obligation",
        chunk_type="obligation_text",
        text=obligation.text,
        section_id=obligation.section_id,
        section_title=None,
        obligation_id=obligation.obligation_id,
        item_id=obligation.obligation_id,
        prefix_title=False,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
      )
    )
  return records


def load_kg_records(
  kg_dir: Path,
  *,
  max_tokens: int,
  overlap_tokens: int,
) -> list[EmbeddableRecord]:
  """Load every ``*.json`` file in ``kg_dir`` into embeddable records."""
  records: list[EmbeddableRecord] = []
  for path in sorted(kg_dir.glob("*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    records.extend(
      kg_file_to_records(
        payload,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
      )
    )
  logger.info("loaded %d KG records from %s", len(records), kg_dir)
  return records


def _item_to_records(
  *,
  law_code: str,
  language: str,
  source_type: str,
  chunk_type: str,
  text: str,
  section_id: str | None,
  section_title: str | None,
  obligation_id: str | None,
  item_id: str,
  prefix_title: bool,
  max_tokens: int,
  overlap_tokens: int,
) -> list[EmbeddableRecord]:
  stripped = text.strip()
  if not stripped:
    logger.info("skipping empty %s %s in %s", source_type, item_id, law_code)
    return []

  records: list[EmbeddableRecord] = []
  title = (section_title or "").strip()
  for index, chunk in enumerate(
    _paragraph_chunks(stripped, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
  ):
    retrieval_text = chunk
    if prefix_title and title:
      retrieval_text = f"{title} — {chunk}"
    records.append(
      EmbeddableRecord(
        clause_id=None,
        document_id=None,
        section_id=section_id,
        section_title=section_title,
        clause_text=stripped,
        retrieval_text=retrieval_text,
        source_type=source_type,
        law_code=law_code,
        obligation_id=obligation_id,
        language=language,
        source={"chunk_index": index, "chunk_type": chunk_type},
      )
    )
  return records


def _paragraph_chunks(text: str, *, max_tokens: int, overlap_tokens: int) -> list[str]:
  chunks: list[str] = []
  for paragraph in text.split("\n\n"):
    paragraph = paragraph.strip()
    if not paragraph:
      continue
    if token_count(paragraph) <= max_tokens:
      chunks.append(paragraph)
    else:
      chunks.extend(
        split_text(paragraph, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
      )
  return chunks
