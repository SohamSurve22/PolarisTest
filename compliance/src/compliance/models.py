"""Structured findings from the compliance engine. Not pipeline ContextBuilder."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ObligationStatus = Literal["covered", "partial", "missing"]


class PenaltyFinding(BaseModel):
  obligation_id: str
  title: str
  amount_crore: float | None = None
  imprisonment_years: float | None = None
  summary: str = ""
  act: str = ""


class MatchedClause(BaseModel):
  clause_id: str
  section_title: str = ""
  text: str = ""


class ObligationFinding(BaseModel):
  obligation_id: str
  title: str
  summary: str = ""
  act: str = ""
  status: ObligationStatus
  score: float = 0.0
  matched_clause_ids: list[str] = Field(default_factory=list)
  matched_clauses: list[MatchedClause] = Field(default_factory=list)


class GapFinding(BaseModel):
  obligation_id: str
  title: str
  status: ObligationStatus
  act: str = ""
  summary: str = ""


class AnalysisResult(BaseModel):
  document_id: str
  source_filename: str = ""
  jurisdiction: str
  applicable_laws: list[str] = Field(default_factory=list)
  obligations: list[ObligationFinding] = Field(default_factory=list)
  gaps: list[GapFinding] = Field(default_factory=list)
  penalties: list[PenaltyFinding] = Field(default_factory=list)


class ReportCounts(BaseModel):
  covered: int = 0
  partial: int = 0
  missing: int = 0
  total: int = 0


class LawNote(BaseModel):
  act: str
  note: str = ""


class ComplianceReport(BaseModel):
  document_id: str
  source_filename: str = ""
  jurisdiction: str = ""
  applicable_laws: list[str] = Field(default_factory=list)
  generated_at: str = ""
  model: str = ""
  counts: ReportCounts = Field(default_factory=ReportCounts)
  executive_summary: str = ""
  narrative_available: bool = False
  law_notes: list[LawNote] = Field(default_factory=list)
  findings: list[ObligationFinding] = Field(default_factory=list)
  penalties: list[PenaltyFinding] = Field(default_factory=list)
  priority_gaps: list[ObligationFinding] = Field(default_factory=list)
  caveats: str = "Not a legal opinion. Statuses come from analysis, not the language model."
