"""Load document_pipeline JSON (flat clauses or nested context/entity shapes)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from document_pipeline.models.clause import Clause, SegmentedDocument

logger = logging.getLogger(__name__)

_MAX_ENTITY_TYPES = 8
_PLAIN_ROLES = frozenset({"STATEMENT", "UNKNOWN", ""})


@dataclass
class EmbeddableSource:
  """A clause plus optional classification/entity tags for retrieval_text."""

  clause: Clause
  role: str | None = None
  entity_types: list[str] = field(default_factory=list)


def clause_from_contextual(cc: object) -> Clause | None:
  """Unwrap a ContextualClause (object or dict) to its inner Clause."""
  classified = _attr(cc, "classified_clause")
  return _clause_from_classified(classified)


def clause_from_entity(ec: object) -> Clause | None:
  """Unwrap an EntityClause (object or dict) to its inner Clause."""
  return clause_from_contextual(_attr(ec, "contextual_clause"))


def decorate_retrieval_text(
  base: str,
  *,
  role: str | None = None,
  entity_types: list[str] | None = None,
) -> str:
  """Append role/entity tags. Skip/split still use raw clause_text."""
  extras: list[str] = []
  role_value = (role or "").strip()
  if role_value and role_value not in _PLAIN_ROLES:
    extras.append(f"(role: {role_value})")
  unique: list[str] = []
  seen: set[str] = set()
  for raw in entity_types or []:
    label = _entity_type_label(raw)
    if not label or label in seen:
      continue
    seen.add(label)
    unique.append(label)
    if len(unique) >= _MAX_ENTITY_TYPES:
      break
  if unique:
    extras.append(f"(entities: {', '.join(unique)})")
  if not extras:
    return base
  return f"{base} {' '.join(extras)}"


def load_embeddable_sources(clauses_dir: Path) -> list[EmbeddableSource]:
  """Load every DOC_*.json as embeddable sources."""
  sources: list[EmbeddableSource] = []
  for path in sorted(clauses_dir.glob("DOC_*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources.extend(_sources_from_payload(payload))
  logger.info("loaded %d embeddable sources from %s", len(sources), clauses_dir)
  return sources


def _sources_from_payload(payload: dict[str, object]) -> list[EmbeddableSource]:
  entity_clauses = payload.get("entity_clauses")
  if isinstance(entity_clauses, list) and entity_clauses:
    return _from_entity_clauses(entity_clauses)

  contextual_clauses = payload.get("contextual_clauses")
  if isinstance(contextual_clauses, list) and contextual_clauses:
    return _from_contextual_clauses(contextual_clauses)

  document = SegmentedDocument.model_validate(payload)
  roles = _roles_from_classifications(payload.get("classifications"))
  entity_map = _entities_from_preview(payload.get("entities"))
  return [
    EmbeddableSource(
      clause=clause,
      role=roles.get(clause.clause_id),
      entity_types=entity_map.get(clause.clause_id, []),
    )
    for clause in document.clauses
  ]


def _from_entity_clauses(items: list[object]) -> list[EmbeddableSource]:
  sources: list[EmbeddableSource] = []
  for item in items:
    clause = clause_from_entity(item)
    if clause is None:
      logger.warning("skipping malformed entity_clause item")
      continue
    classified = _attr(_attr(item, "contextual_clause"), "classified_clause")
    sources.append(
      EmbeddableSource(
        clause=clause,
        role=_role_value(_attr(classified, "role")),
        entity_types=_entity_types_from_list(_attr(item, "entities")),
      )
    )
  return sources


def _from_contextual_clauses(items: list[object]) -> list[EmbeddableSource]:
  sources: list[EmbeddableSource] = []
  for item in items:
    clause = clause_from_contextual(item)
    if clause is None:
      logger.warning("skipping malformed contextual_clause item")
      continue
    classified = _attr(item, "classified_clause")
    sources.append(
      EmbeddableSource(
        clause=clause,
        role=_role_value(_attr(classified, "role")),
      )
    )
  return sources


def _clause_from_classified(classified: object) -> Clause | None:
  raw = _attr(classified, "clause")
  if raw is None:
    return None
  if isinstance(raw, Clause):
    return raw
  if isinstance(raw, dict):
    try:
      return Clause.model_validate(raw)
    except ValidationError:
      logger.warning("skipping clause that failed validation")
      return None
  return None


def _roles_from_classifications(raw: object) -> dict[str, str]:
  roles: dict[str, str] = {}
  if not isinstance(raw, list):
    return roles
  for item in raw:
    clause_id = _attr(item, "clause_id")
    role = _role_value(_attr(item, "role"))
    if isinstance(clause_id, str) and role:
      roles[clause_id] = role
  return roles


def _entities_from_preview(raw: object) -> dict[str, list[str]]:
  mapped: dict[str, list[str]] = {}
  if not isinstance(raw, list):
    return mapped
  for item in raw:
    clause_id = _attr(item, "clause_id")
    label = _entity_type_label(_attr(item, "entity_type"))
    if isinstance(clause_id, str) and label:
      mapped.setdefault(clause_id, []).append(label)
  return mapped


def _entity_types_from_list(raw: object) -> list[str]:
  if not isinstance(raw, list):
    return []
  labels: list[str] = []
  for item in raw:
    labels.append(_entity_type_label(_attr(item, "entity_type") if not isinstance(item, str) else item))
  return [label for label in labels if label]


def _entity_type_label(value: object) -> str:
  if value is None:
    return ""
  if hasattr(value, "value"):
    value = value.value
  return str(value).strip()


def _role_value(value: object) -> str | None:
  if value is None:
    return None
  if hasattr(value, "value"):
    value = value.value
  text = str(value).strip()
  return text or None


def _attr(obj: object, key: str) -> object:
  if obj is None:
    return None
  if isinstance(obj, dict):
    return obj.get(key)
  return getattr(obj, key, None)
