"""Catalog of India website-privacy obligations and linked penalties."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from policy_compare.law_loader import load_law_chunks
from policy_compare.models import LawChunk

DUTY_CHUNK_TYPES: frozenset[str] = frozenset({
  "obligation",
  "duty",
  "compliance_requirement",
})

_PENALTY_RELS = frozenset({"CITES", "PENALISES", "TRIGGERS_PENALTY"})


@dataclass
class PenaltyLink:
  penalty_id: str
  title: str
  summary: str
  act: str
  amount_crore: float | None
  imprisonment_years: float | None
  obligation_ids: tuple[str, ...]


@dataclass
class LawCatalog:
  obligations: list[LawChunk]
  penalties: list[PenaltyLink] = field(default_factory=list)

  def penalties_for(self, obligation_id: str) -> list[PenaltyLink]:
    return [row for row in self.penalties if obligation_id in row.obligation_ids]


def load_catalog(paths: list[Path]) -> LawCatalog:
  """Website-privacy duties plus penalty rows linked by CITES / TRIGGERS_PENALTY / own amount."""
  duties = [
    chunk
    for chunk in load_law_chunks(paths)
    if (chunk.chunk_type or "") in DUTY_CHUNK_TYPES
  ]
  duty_ids = {chunk.doc_id for chunk in duties}
  penalties: list[PenaltyLink] = []
  seen: set[tuple[str, tuple[str, ...]]] = set()

  for path in paths:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
      continue
    for raw in payload:
      if not isinstance(raw, dict):
        continue
      doc_id = str(raw.get("doc_id") or "")
      props = raw.get("node_properties") or {}
      amount = _float_or_none(props.get("penalty_amount_crore"))
      years = _float_or_none(props.get("imprisonment_years"))
      chunk_type = raw.get("chunk_type")
      rels = raw.get("relationships") or []
      cited = tuple(
        sorted(
          {
            str(rel.get("target_id"))
            for rel in rels
            if rel.get("type") in _PENALTY_RELS and str(rel.get("target_id") or "") in duty_ids
          }
        )
      )
      if chunk_type == "penalty":
        targets = cited
        if not targets and amount is None and years is None:
          continue
        if not targets and doc_id in duty_ids:
          targets = (doc_id,)
        link = _penalty_link(raw, targets or (), amount, years)
        key = (link.penalty_id, link.obligation_ids)
        if key not in seen:
          seen.add(key)
          penalties.append(link)
        continue

      if doc_id in duty_ids and (amount is not None or years is not None or cited):
        targets = (doc_id,) if doc_id else cited
        extra = tuple(oid for oid in cited if oid != doc_id)
        link = _penalty_link(raw, tuple(sorted(set(targets + extra))), amount, years)
        key = (link.penalty_id, link.obligation_ids)
        if key not in seen:
          seen.add(key)
          penalties.append(link)

  return LawCatalog(obligations=duties, penalties=penalties)


def _penalty_link(
  raw: dict[str, Any],
  obligation_ids: tuple[str, ...],
  amount: float | None,
  years: float | None,
) -> PenaltyLink:
  metadata = raw.get("metadata") or {}
  return PenaltyLink(
    penalty_id=str(raw.get("doc_id") or ""),
    title=str(raw.get("title") or raw.get("doc_id") or ""),
    summary=str(raw.get("plain_english_summary") or raw.get("clause_text") or "").strip(),
    act=str(metadata.get("act") or ""),
    amount_crore=amount,
    imprisonment_years=years,
    obligation_ids=obligation_ids,
  )


def _float_or_none(value: Any) -> float | None:
  if value is None or value is False:
    return None
  try:
    return float(value)
  except (TypeError, ValueError):
    return None
