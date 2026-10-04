"""OpenIE-style subject-predicate-object propositions. Not GraphIR."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawProposition:
  subject: str
  predicate: str
  object: str
  evidence: str
  source_clause_id: str
  document_id: str = ""
  confidence: float | None = None
  section_title: str = ""
  metadata: dict[str, Any] = field(default_factory=dict)
