"""Load the four statute JSON files into filtered LawChunk rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from policy_compare.models import LawChunk
from policy_compare.topics import KEEP_CHUNK_TYPES, KEPT_TOPICS

_IT_ACT = "IT_ACT_2000"


def load_law_chunks(paths: list[Path]) -> list[LawChunk]:
  """Read statute JSON arrays and keep website-privacy law chunks."""
  chunks: list[LawChunk] = []
  for path in paths:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
      msg = f"Expected a JSON array in {path}"
      raise ValueError(msg)
    for raw in payload:
      chunk = _maybe_chunk(raw)
      if chunk is not None:
        chunks.append(chunk)
  return chunks


def _maybe_chunk(raw: dict[str, Any]) -> LawChunk | None:
  if raw.get("node_label") != "Section":
    return None

  rels = raw.get("relationships") or []
  topic_ids = [
    rel["target_id"]
    for rel in rels
    if rel.get("type") == "TAGGED_WITH" and rel.get("target_id") in KEPT_TOPICS
  ]
  if not topic_ids:
    return None
  entity_ids = sorted({
    str(rel["target_id"])
    for rel in rels
    if rel.get("type") == "IMPOSES_DUTY_ON" and rel.get("target_id")
  })

  chunk_type = raw.get("chunk_type")
  props = raw.get("node_properties") or {}
  is_mandatory = bool(props.get("is_mandatory"))
  if chunk_type not in KEEP_CHUNK_TYPES and not is_mandatory:
    return None

  metadata = raw.get("metadata") or {}
  act = str(metadata.get("act") or "")
  if act == _IT_ACT and not topic_ids:
    return None

  summary = (raw.get("plain_english_summary") or raw.get("clause_text") or "").strip()
  text = (raw.get("clause_text") or "").strip()
  if not summary and not text:
    return None

  return LawChunk(
    doc_id=str(raw.get("doc_id") or ""),
    title=str(raw.get("title") or raw.get("doc_id") or ""),
    summary=summary,
    clause_text=text,
    chunk_type=chunk_type,
    act=act,
    is_mandatory=is_mandatory,
    topic_ids=sorted(set(topic_ids)),
    entity_ids=entity_ids,
  )
