"""Map OpenIE surface forms onto Ideal Graph labels and relations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import unicodedata

from graph_builder.graph_models import ALLOWED_NODE_LABELS, ALLOWED_RELATIONSHIP_TYPES
from graph_builder.ontology import EntityAlias, load_entity_aliases, load_relation_aliases, triple_allowed

EntityStatus = Literal["ok", "AMBIGUOUS", "UNMAPPED"]

_CONTEXT_PREDICATES = frozenset({"purpose", "for", "duration", "as long as"})


@dataclass(frozen=True)
class CanonicalEntity:
  canonical_name: str
  label: str
  status: EntityStatus = "ok"


def _norm(text: str) -> str:
  return " ".join(unicodedata.normalize("NFKC", text or "").lower().split())


def normalize_entity(raw: str) -> CanonicalEntity:
  """Exact canonical, then alias. Embeddings are never auto-accepted."""
  key = _norm(raw)
  if not key:
    return CanonicalEntity(canonical_name="", label="", status="UNMAPPED")

  aliases = load_entity_aliases()
  if key in aliases:
    row = aliases[key]
    label = row["label"]
    if label not in ALLOWED_NODE_LABELS:
      return CanonicalEntity(canonical_name=key, label="", status="UNMAPPED")
    return CanonicalEntity(canonical_name=row["canonical_name"], label=label, status="ok")

  hits: list[EntityAlias] = []
  for alias_key, row in aliases.items():
    if len(alias_key) < 5:
      continue
    if alias_key in key or key in alias_key:
      hits.append(row)
  if len(hits) == 1:
    row = hits[0]
    return CanonicalEntity(canonical_name=row["canonical_name"], label=row["label"], status="ok")
  if len(hits) > 1:
    labels = {item["label"] for item in hits}
    names = {item["canonical_name"] for item in hits}
    if len(labels) == 1 and len(names) == 1:
      return CanonicalEntity(
        canonical_name=next(iter(names)),
        label=next(iter(labels)),
        status="ok",
      )
    return CanonicalEntity(canonical_name=key, label="", status="AMBIGUOUS")

  return CanonicalEntity(canonical_name=key, label="", status="UNMAPPED")


def canonical_relation_type(raw_predicate: str) -> str | None:
  """Map a predicate phrase to an allowed relationship type, or None."""
  key = _norm(raw_predicate)
  if not key:
    return None
  compact = key.replace(" ", "_").upper()
  if compact in ALLOWED_RELATIONSHIP_TYPES:
    return compact
  return load_relation_aliases().get(key)


def normalize_relation(
  raw_predicate: str,
  source_label: str,
  target_label: str,
) -> str | None:
  """Map a predicate to a canonical rel if the triple is allowed."""
  canonical = canonical_relation_type(raw_predicate)
  if canonical is None:
    return None
  if not triple_allowed(source_label, canonical, target_label):
    return None
  return canonical


def is_context_predicate(raw_predicate: str) -> bool:
  return _norm(raw_predicate) in _CONTEXT_PREDICATES
