"""Data models for clause semantic enrichment.

These models represent the semantic meaning extracted from a legal
clause — the obligations, permissions, prohibitions, etc. embedded
in the text.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Obligation:
    """A single obligation extracted from a legal clause.

    Attributes:
        subject:  The entity that must perform the action.
        action:   The required behaviour (verb phrase).
        object:   What the action applies to.
        condition: Circumstance under which the obligation applies (optional).
        exception: Carve-out or exclusion to the obligation (optional).
    """

    subject: str = ""
    action: str = ""
    object: str = ""
    condition: str | None = None
    exception: str | None = None


@dataclass
class ClauseMeaning:
    """The full semantic meaning extracted from a single clause.

    Attributes:
        clause_id:    Stable identifier of the source clause.
        obligations:  Zero or more obligations found in the clause text.
    """

    clause_id: str = ""
    obligations: list[Obligation] = field(default_factory=list)
