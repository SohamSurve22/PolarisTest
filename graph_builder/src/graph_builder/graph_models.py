"""Allowed node labels and relationship types for the knowledge graph."""

from __future__ import annotations

ALLOWED_NODE_LABELS: frozenset[str] = frozenset(
  {
    "LawVersion",
    "Chapter",
    "Section",
    "SubSection",
    "Rule",
    "Definition",
    "Obligation",
    "Requirement",
    "Exception",
    "Penalty",
    "Authority",
    "Entity",
    "Actor",
    "DocumentType",
    "LegalConcept",
    "Clause",
    "PrivacyPractice",
    "SecurityPractice",
    "SensitiveData",
    "PersonalData",
    "Consent",
    "RetentionPolicy",
    "UnresolvedReference",
  }
)

ALLOWED_RELATIONSHIP_TYPES: frozenset[str] = frozenset(
  {
    "HAS_CHAPTER",
    "HAS_SECTION",
    "HAS_SUBSECTION",
    "HAS_RULE",
    "DEFINES",
    "IMPOSES",
    "REQUIRES",
    "EXEMPTS",
    "PENALIZES",
    "ENFORCED_BY",
    "APPLIES_TO",
    "PROCESSES",
    "COLLECTS",
    "RETURNS",
    "RETAINS",
    "SHARES",
    "USES",
    "HAS_EXCEPTION",
    "REFERENCES",
    "DERIVED_FROM",
    "UNRESOLVED_REFERENCE",
  }
)
