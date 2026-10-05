"""Path B wiring helper (applied inside service.py via str_replace)."""

from __future__ import annotations

from dataclasses import dataclass

from compliance.jev import JevClient

jev = JevClient()


@dataclass(frozen=True)
class AppliedDuty:
    obligation_id: str
    act: str
    title: str
    summary: str
    requirement_elements: list[dict[str, object]]
