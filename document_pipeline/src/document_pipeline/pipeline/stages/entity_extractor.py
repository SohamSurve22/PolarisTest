"""Stage 7: Entity Extractor — legal entity detection.

Detects legal entities appearing in every clause using lightweight
dictionary lookup and regex patterns.  No LLM, transformer, or
embedding is used in this version.

Each detector implements the same ``detect(text: str) -> list[Entity]``
interface so a future transformer-based detector can replace any of them
without changing the pipeline.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.context import ContextDocument, ContextualClause, Reference
from document_pipeline.models.entity import Entity, EntityClause, EntityDocument, EntityType

# ---------------------------------------------------------------------------
# lookup dictionaries  (lower-cased keys, Title Case canonicals)
# ---------------------------------------------------------------------------

_ACTOR_TERMS: dict[str, str] = {
    "data fiduciary": "Data Fiduciary",
    "data principal": "Data Principal",
    "board": "Board",
    "central government": "Central Government",
    "state government": "State Government",
    "controller": "Controller",
    "processor": "Processor",
    "authority": "Authority",
    "court": "Court",
    "tribunal": "Tribunal",
}

_DOCUMENT_TERMS: dict[str, str] = {
    "dpdp act": "DPDP Act",
    "it act": "IT Act",
    "constitution": "Constitution",
    "rules": "Rules",
    "regulations": "Regulations",
}

_OBJECT_TERMS: dict[str, str] = {
    "personal data": "personal data",
    "sensitive personal data": "sensitive personal data",
    "consent": "consent",
    "notice": "notice",
    "request": "request",
    "complaint": "complaint",
    "application": "application",
    "technical measures": "technical measures",
    "security safeguards": "security safeguards",
}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_ID_COUNTER: list[int] = [0]


def _next_entity_id() -> str:
  _ID_COUNTER[0] += 1
  return f"E{_ID_COUNTER[0]:03d}"


def _reset_counter() -> None:
  _ID_COUNTER[0] = 0


def _dict_detect(
    text: str,
    terms: dict[str, str],
    entity_type: EntityType,
    method: str,
) -> list[Entity]:
  """Find all occurrences of dictionary terms in *text*."""
  found: list[Entity] = []
  seen: set[tuple[int, int]] = set()
  lower = text.lower()

  for key, canonical in terms.items():
    pattern = re.compile(r"(?<!\w)" + re.escape(key) + r"(?!\w)", re.IGNORECASE)
    for match in pattern.finditer(text):
      span = (match.start(), match.end())
      if span not in seen:
        seen.add(span)
        found.append(
          Entity(
            entity_id=_next_entity_id(),
            entity_text=match.group(0),
            entity_type=entity_type,
            start_offset=match.start(),
            end_offset=match.end(),
            confidence=0.95,
            detection_method=method,
          ),
        )

  found.sort(key=lambda e: e.start_offset)
  return found


# ---------------------------------------------------------------------------
# ActorDetector
# ---------------------------------------------------------------------------

@dataclass
class ActorDetector:
  """Detects legal actors (Data Fiduciary, Board, Court, …)."""

  def detect(self, text: str) -> list[Entity]:
    return _dict_detect(text, _ACTOR_TERMS, EntityType.LEGAL_ACTOR, "actor_dict")


# ---------------------------------------------------------------------------
# DocumentDetector
# ---------------------------------------------------------------------------

@dataclass
class DocumentDetector:
  """Detects legal document references (DPDP Act, IT Act, …)."""

  def detect(self, text: str) -> list[Entity]:
    return _dict_detect(text, _DOCUMENT_TERMS, EntityType.LEGAL_DOCUMENT, "document_dict")


# ---------------------------------------------------------------------------
# ObjectDetector
# ---------------------------------------------------------------------------

@dataclass
class ObjectDetector:
  """Detects legal objects (personal data, consent, notice, …)."""

  def detect(self, text: str) -> list[Entity]:
    return _dict_detect(text, _OBJECT_TERMS, EntityType.LEGAL_OBJECT, "object_dict")


# ---------------------------------------------------------------------------
# TimeDetector
# ---------------------------------------------------------------------------

_TIME_PATTERNS: list[tuple[str, str, float]] = [
    (r"\b\d+\s*days?\b", "time_duration", 0.9),
    (r"\bimmediately\b", "time_adverb", 0.9),
    (r"\bwithin\s+\d+\s*days?\b", "time_duration", 0.9),
    (r"\bbefore\s+processing\b", "time_event", 0.85),
]

_DATE_PATTERNS: list[tuple[str, str, float]] = [
    (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "date_explicit", 1.0),
    (r"\b\d{4}-\d{2}-\d{2}\b", "date_iso", 1.0),
]


@dataclass
class TimeDetector:
  """Detects time and date expressions (30 days, immediately, …)."""

  _month: str = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"

  def detect(self, text: str) -> list[Entity]:
    entities: list[Entity] = []
    seen: set[tuple[int, int]] = set()

    for pattern, method, conf in _TIME_PATTERNS:
      for match in re.finditer(pattern, text, re.IGNORECASE):
        span = (match.start(), match.end())
        if span not in seen:
          seen.add(span)
          entities.append(
            Entity(
              entity_id=_next_entity_id(),
              entity_text=match.group(0),
              entity_type=EntityType.TIME,
              start_offset=match.start(),
              end_offset=match.end(),
              confidence=conf,
              detection_method=method,
            ),
          )

    date_pattern = rf"\b\d{{1,2}}\s+{self._month}\s+\d{{4}}\b"
    for match in re.finditer(date_pattern, text):
      span = (match.start(), match.end())
      if span not in seen:
        seen.add(span)
        entities.append(
          Entity(
            entity_id=_next_entity_id(),
            entity_text=match.group(0),
            entity_type=EntityType.DATE,
            start_offset=match.start(),
            end_offset=match.end(),
            confidence=1.0,
            detection_method="date_explicit",
          ),
        )

    for pattern, method, conf in _DATE_PATTERNS:
      for match in re.finditer(pattern, text):
        span = (match.start(), match.end())
        if span not in seen:
          seen.add(span)
          entities.append(
            Entity(
              entity_id=_next_entity_id(),
              entity_text=match.group(0),
              entity_type=EntityType.DATE,
              start_offset=match.start(),
              end_offset=match.end(),
              confidence=conf,
              detection_method=method,
            ),
          )

    entities.sort(key=lambda e: e.start_offset)
    return entities


# ---------------------------------------------------------------------------
# ReferenceEntityDetector
# ---------------------------------------------------------------------------

@dataclass
class ReferenceEntityDetector:
  """Converts Stage-2 Reference objects into LAW_REFERENCE entities."""

  def detect_from_references(self, references: list[Reference]) -> list[Entity]:
    entities: list[Entity] = []
    for ref in references:
      entities.append(
        Entity(
          entity_id=_next_entity_id(),
          entity_text=ref.reference_text,
          entity_type=EntityType.LAW_REFERENCE,
          start_offset=ref.start,
          end_offset=ref.end,
          confidence=1.0,
          detection_method="reference_detector",
        ),
      )
    return entities


# ---------------------------------------------------------------------------
# EntityMerger
# ---------------------------------------------------------------------------

@dataclass
class EntityMerger:
  """Merges entity lists from multiple detectors, deduplicating by span.

  The longest match wins when spans overlap.
  """

  def merge(self, *entity_lists: list[Entity]) -> list[Entity]:
    all_entities: list[Entity] = []
    for lst in entity_lists:
      all_entities.extend(lst)

    all_entities.sort(key=lambda e: (e.start_offset, -e.end_offset))

    merged: list[Entity] = []
    for ent in all_entities:
      if not merged:
        merged.append(ent)
        continue

      prev = merged[-1]
      if ent.start_offset >= prev.end_offset:
        merged.append(ent)
      elif ent.end_offset > prev.end_offset:
        merged.append(ent)

    return merged


# ---------------------------------------------------------------------------
# EntityExtractor
# ---------------------------------------------------------------------------

EntityDetectorFn = Callable[[str], list[Entity]]


class EntityExtractor(BaseProcessor[ContextDocument, EntityDocument]):
  """Detects legal entities in every clause using replaceable detectors.

  Default detectors use dictionary lookup and regex.  Pass custom detectors
  to the constructor to replace individual components with transformer-based
  alternatives.
  """

  def __init__(
    self,
    actor_detector: ActorDetector | None = None,
    document_detector: DocumentDetector | None = None,
    object_detector: ObjectDetector | None = None,
    time_detector: TimeDetector | None = None,
    reference_entity_detector: ReferenceEntityDetector | None = None,
    entity_merger: EntityMerger | None = None,
  ) -> None:
    self._actor = actor_detector or ActorDetector()
    self._document = document_detector or DocumentDetector()
    self._object = object_detector or ObjectDetector()
    self._time = time_detector or TimeDetector()
    self._reference_entity = reference_entity_detector or ReferenceEntityDetector()
    self._merger = entity_merger or EntityMerger()

  def process(self, input_data: ContextDocument) -> EntityDocument:
    _reset_counter()
    entity_clauses: list[EntityClause] = []

    for cc in input_data.contextual_clauses:
      text = cc.classified_clause.clause.clause_text

      actors = self._actor.detect(text)
      docs = self._document.detect(text)
      objects = self._object.detect(text)
      times = self._time.detect(text)
      law_refs = self._reference_entity.detect_from_references(cc.detected_references)

      entities = self._merger.merge(actors, docs, objects, times, law_refs)

      entity_clauses.append(
        EntityClause(contextual_clause=cc, entities=entities),
      )

    return EntityDocument(
      metadata=input_data.metadata,
      entity_clauses=entity_clauses,
    )
