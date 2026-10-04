"""Canonical Ideal Graph triples and alias tables.

Vocabulary (labels and relationship types) lives in ``graph_models``.
This module only records which (source, rel, target) combinations are legal
and how OpenIE surface forms map onto that vocabulary.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from graph_builder.graph_models import ALLOWED_NODE_LABELS, ALLOWED_RELATIONSHIP_TYPES

_DATA = Path(__file__).parent / "data"


class EntityAlias(TypedDict):
  canonical_name: str
  label: str


def _expand(
  sources: frozenset[str],
  rel: str,
  targets: frozenset[str],
) -> set[tuple[str, str, str]]:
  return {(source, rel, target) for source in sources for target in targets}


_ACTOR = frozenset({"Actor", "Entity"})
_DATA_CAT = frozenset({"PersonalData", "SensitiveData"})
_LAW_UNIT = frozenset({"LawVersion", "Chapter", "Section", "SubSection", "Rule"})
_REF_SRC = frozenset({
  "Clause",
  "Section",
  "SubSection",
  "Rule",
  "Chapter",
  "Obligation",
  "Definition",
  "LawVersion",
})
_REF_TGT = _REF_SRC | frozenset({"UnresolvedReference"})

ALLOWED_TRIPLES: frozenset[tuple[str, str, str]] = frozenset(
  _expand(frozenset({"LawVersion"}), "HAS_CHAPTER", frozenset({"Chapter"}))
  | _expand(frozenset({"LawVersion", "Chapter"}), "HAS_SECTION", frozenset({"Section"}))
  | _expand(frozenset({"Section"}), "HAS_SUBSECTION", frozenset({"SubSection"}))
  | _expand(_LAW_UNIT, "HAS_RULE", frozenset({"Rule"}))
  | _expand(_LAW_UNIT, "DEFINES", frozenset({"Definition"}))
  | _expand(_LAW_UNIT, "IMPOSES", frozenset({"Obligation"}))
  | _expand(
    frozenset({"Obligation"}),
    "REQUIRES",
    frozenset({"Requirement", "Consent", "PrivacyPractice", "SecurityPractice", "RetentionPolicy"}),
  )
  | _expand(frozenset({"Exception"}) | _LAW_UNIT, "EXEMPTS", frozenset({"Obligation"}))
  | _expand(frozenset({"Penalty"}), "PENALIZES", frozenset({"Obligation"}))
  | _expand(frozenset({"Obligation", "Penalty"}), "ENFORCED_BY", frozenset({"Authority"}))
  | _expand(_LAW_UNIT | frozenset({"Obligation"}), "APPLIES_TO", _ACTOR | frozenset({"DocumentType"}))
  | _expand(_ACTOR | frozenset({"PrivacyPractice"}), "PROCESSES", _DATA_CAT)
  | _expand(_ACTOR, "COLLECTS", _DATA_CAT)
  | _expand(_ACTOR | frozenset({"Authority"}), "RETURNS", _DATA_CAT)
  | _expand(_ACTOR, "RETAINS", _DATA_CAT | frozenset({"RetentionPolicy"}))
  | _expand(_ACTOR, "SHARES", _ACTOR | _DATA_CAT)
  | _expand(_ACTOR, "USES", _DATA_CAT | frozenset({"PrivacyPractice", "SecurityPractice", "Consent"}))
  | _expand(frozenset({"Obligation"}), "HAS_EXCEPTION", frozenset({"Exception"}))
  | _expand(_REF_SRC, "REFERENCES", _REF_TGT)
  | _expand(
    frozenset({"Clause", "Obligation", "Definition"}),
    "DERIVED_FROM",
    _LAW_UNIT | frozenset({"Clause"}),
  )
  | _expand(_REF_SRC | _ACTOR, "UNRESOLVED_REFERENCE", frozenset({"UnresolvedReference"}))
  | _expand(_LAW_UNIT | frozenset({"Clause"}), "HAS_OBLIGATION", frozenset({"Obligation"}))
)


def _assert_vocabulary() -> None:
  for source, rel, target in ALLOWED_TRIPLES:
    if source not in ALLOWED_NODE_LABELS or target not in ALLOWED_NODE_LABELS:
      raise RuntimeError(f"triple uses unknown label: {(source, rel, target)}")
    if rel not in ALLOWED_RELATIONSHIP_TYPES:
      raise RuntimeError(f"triple uses unknown rel: {(source, rel, target)}")


_assert_vocabulary()


def triple_allowed(source_label: str, rel: str, target_label: str) -> bool:
  return (source_label, rel, target_label) in ALLOWED_TRIPLES


@lru_cache(maxsize=1)
def load_relation_aliases() -> dict[str, str]:
  payload = json.loads((_DATA / "relation_aliases.json").read_text(encoding="utf-8"))
  return {str(key).lower(): str(value) for key, value in payload.items()}


@lru_cache(maxsize=1)
def load_entity_aliases() -> dict[str, EntityAlias]:
  payload = json.loads((_DATA / "entity_aliases.json").read_text(encoding="utf-8"))
  aliases: dict[str, EntityAlias] = {}
  for key, value in payload.items():
    aliases[str(key).lower()] = {
      "canonical_name": str(value["canonical_name"]),
      "label": str(value["label"]),
    }
  return aliases
