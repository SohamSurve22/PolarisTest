"""Unmapped / ambiguous OpenIE mappings. Never become GraphIR vocabulary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MappingStatus = Literal[
  "UNMAPPED_ENTITY",
  "UNMAPPED_RELATION",
  "AMBIGUOUS_ENTITY",
  "AMBIGUOUS_RELATION",
  "INVALID_RELATION_COMBINATION",
]


@dataclass
class MappingFailure:
  status: MappingStatus
  raw_predicate: str
  subject: str
  object: str
  evidence: str
  reason: str
  source_clause_id: str = ""
  document_id: str = ""
  confidence: float | None = None
  metadata: dict[str, Any] = field(default_factory=dict)

  def to_dict(self) -> dict[str, Any]:
    return {
      "status": self.status,
      "rawPredicate": self.raw_predicate,
      "subject": self.subject,
      "object": self.object,
      "evidence": self.evidence,
      "reason": self.reason,
      "sourceClauseId": self.source_clause_id,
      "documentId": self.document_id,
      "confidence": self.confidence,
      "metadata": self.metadata,
    }
