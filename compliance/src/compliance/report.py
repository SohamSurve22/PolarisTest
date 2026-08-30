"""LLM narrative over AnalysisResult. The model explains; it does not decide status."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from compliance.models import (
  AnalysisResult,
  ComplianceReport,
  LawNote,
  ObligationFinding,
  PenaltyFinding,
  ReportCounts,
)

ChatFn = Callable[[str, str], str]

DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
NARRATIVE_UNAVAILABLE = "Narrative unavailable. The table below is from automated analysis only."

SYSTEM = """You write extra briefing sentences for a client-facing compliance memo.
The engine already finalized statuses, per-law counts, and Themes.
You must not invent laws, obligation ids, statuses, penalties, or coverage verdicts.
Do not write law_notes themes. Do not start with However. Do not say "compliance framework".
Say "this policy" when you refer to the document.
Return only this object:
{"executive_summary": string, "law_notes": []}
executive_summary: 2 to 4 sentences after the engine scoreboard. Name what is in place
from covered titles, then remaining gap topics. Do not quote covered/partial/missing counts.
"""

THEME_LIMIT = 3
PRIORITY_GAPS_CAP = 5
_FRAMEWORK = re.compile(r"the compliance framework|compliance framework", re.IGNORECASE)
_HOWEVER = re.compile(r"^however,?\s+", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

REPORT_SCHEMA = {
  "type": "object",
  "properties": {
    "executive_summary": {"type": "string"},
    "law_notes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "act": {"type": "string"},
          "theme": {"type": "string"},
        },
        "required": ["act", "theme"],
      },
    },
  },
  "required": ["executive_summary", "law_notes"],
}


class ReportError(Exception):
  """Chat model unavailable or returned unusable JSON."""


def verdict_sentence(act: str, counts: ReportCounts) -> str:
  return f"{act}: {counts.covered} covered, {counts.partial} partial, {counts.missing} missing."


def scoreboard_sentence(counts: ReportCounts) -> str:
  return (
    f"This policy covers {counts.covered} of {counts.total} applicable duties, "
    f"with {counts.partial} partial, {counts.missing} missing, "
    f"{counts.undetermined} undetermined. {counts.not_applicable} duties were not applicable. "
    "Missing policy language is not a finding of legal violation."
  )


def engine_themes(analysis: AnalysisResult, act: str) -> str:
  titles = _by_law_titles(analysis).get(act) or {"missing": [], "partial": []}
  picked: list[str] = []
  seen: set[str] = set()
  for title in list(titles.get("missing") or []) + list(titles.get("partial") or []):
    text = str(title or "").strip()
    if not text or text in seen:
      continue
    seen.add(text)
    picked.append(text)
    if len(picked) >= THEME_LIMIT:
      break
  return "; ".join(picked)


def compact_payload(analysis: AnalysisResult) -> dict:
  counts = _counts(analysis)
  titles = _by_law_titles(analysis)
  buckets = _by_law_counts(analysis)
  by_law = []
  for act in _ordered_acts(analysis):
    act_counts = buckets.get(act) or ReportCounts()
    act_titles = titles.get(act) or {"covered": [], "partial": [], "missing": []}
    by_law.append(
      {
        "act": act,
        "counts": {
          "covered": act_counts.covered,
          "partial": act_counts.partial,
          "missing": act_counts.missing,
          "total": act_counts.total,
        },
        "titles": act_titles,
      }
    )
  return {
    "document_id": analysis.document_id,
    "jurisdiction": analysis.jurisdiction,
    "applicable_laws": list(analysis.applicable_laws),
    "counts": counts.model_dump(),
    "by_law": by_law,
  }


def assemble_report(
  analysis: AnalysisResult,
  *,
  generated_at: str,
  model: str = "",
) -> ComplianceReport:
  counts = _counts(analysis)
  allowed = {row.obligation_id for row in analysis.obligations}
  penalties = [
    row
    for row in analysis.penalties
    if row.obligation_id in allowed
    and (row.amount_crore is not None or row.imprisonment_years is not None)
  ]
  return ComplianceReport(
    document_id=analysis.document_id,
    source_filename=analysis.source_filename,
    jurisdiction=analysis.jurisdiction,
    applicable_laws=list(analysis.applicable_laws),
    generated_at=generated_at,
    model=model,
    counts=counts,
    executive_summary=scoreboard_sentence(counts),
    findings=list(analysis.obligations),
    penalties=penalties,
    priority_gaps=_priority_gaps(analysis.obligations, penalties),
    law_notes=_verdict_notes(analysis),
    narrative_available=False,
  )


def generate_report(
  analysis: AnalysisResult,
  *,
  chat: ChatFn | None = None,
  report_dir: Path | None = None,
  model: str | None = None,
  generated_at: str | None = None,
) -> ComplianceReport:
  when = generated_at or _now_iso()
  model_name = model or os.environ.get("POLARIS_CHAT_MODEL", DEFAULT_MODEL)
  report = assemble_report(analysis, generated_at=when, model="")
  chat_fn = chat or default_chat
  try:
    raw = chat_fn(SYSTEM, json.dumps(compact_payload(analysis), ensure_ascii=False))
    parsed = _parse_json(raw)
    summary = str(parsed.get("executive_summary") or "").strip()
    if not summary:
      raise ReportError("empty executive_summary")
  except (ReportError, json.JSONDecodeError, TypeError, ValueError):
    _persist(report, analysis.document_id, report_dir)
    return report

  report.executive_summary = _compose_summary(scoreboard_sentence(report.counts), summary, report.counts)
  report.narrative_available = True
  report.model = model_name
  _persist(report, analysis.document_id, report_dir)
  return report


def default_chat(system_prompt: str, user_prompt: str) -> str:
  import httpx

  model = os.environ.get("POLARIS_CHAT_MODEL", DEFAULT_MODEL)
  base = os.environ.get("POLARIS_OLLAMA_URL", "http://localhost:11434").rstrip("/")
  url = f"{base}/api/chat"
  payload = {
    "model": model,
    "messages": [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_prompt},
    ],
    "stream": False,
    "format": REPORT_SCHEMA,
    "options": {"temperature": 0.2, "num_ctx": 8192},
  }
  try:
    response = httpx.post(url, json=payload, timeout=180.0)
    response.raise_for_status()
  except httpx.HTTPError as exc:
    raise ReportError(f"local LLM request failed ({model}): {exc}") from exc
  data = response.json()
  content = data.get("message", {}).get("content", "")
  if not content:
    raise ReportError(f"empty response from local model {model}")
  return content


_SEV_WEIGHT = {"critical": 5, "high": 4, "medium": 3, "low": 1}
_STATUS_WEIGHT = {"covered": 1.0, "partial": 0.5, "undetermined": 0.25}


def _counts(analysis: AnalysisResult) -> ReportCounts:
  covered = sum(1 for row in analysis.obligations if row.status == "covered")
  partial = sum(1 for row in analysis.obligations if row.status == "partial")
  missing = sum(1 for row in analysis.obligations if row.status == "missing")
  undetermined = sum(1 for row in analysis.obligations if row.status == "undetermined")
  conflict = sum(1 for row in analysis.obligations if row.status == "conflict")
  violation = sum(1 for row in analysis.obligations if row.status == "violation")
  not_applicable = sum(1 for row in analysis.obligations if row.status == "not_applicable")
  applicable = [row for row in analysis.obligations if row.status != "not_applicable"]
  return ReportCounts(
    covered=covered,
    partial=partial,
    missing=missing,
    undetermined=undetermined,
    conflict=conflict,
    violation=violation,
    not_applicable=not_applicable,
    total=len(applicable),
    weighted_pct=_weighted_pct(applicable),
  )


def _weighted_pct(rows: list[ObligationFinding]) -> float:
  denom = 0.0
  numer = 0.0
  for row in rows:
    weight = _SEV_WEIGHT.get(row.severity or "medium", 3)
    denom += weight
    numer += weight * _STATUS_WEIGHT.get(row.status, 0.0)
  if denom <= 0:
    return 0.0
  return round(100.0 * numer / denom, 1)


def _by_law_counts(analysis: AnalysisResult) -> dict[str, ReportCounts]:
  buckets: dict[str, ReportCounts] = {}
  for row in analysis.obligations:
    act = row.act or ""
    counts = buckets.setdefault(act, ReportCounts())
    if row.status == "not_applicable":
      counts.not_applicable += 1
      continue
    if row.status == "covered":
      counts.covered += 1
    elif row.status == "partial":
      counts.partial += 1
    elif row.status == "undetermined":
      counts.undetermined += 1
    elif row.status == "conflict":
      counts.conflict += 1
    elif row.status == "violation":
      counts.violation += 1
    else:
      counts.missing += 1
    counts.total += 1
  return buckets


def _by_law_titles(analysis: AnalysisResult) -> dict[str, dict[str, list[str]]]:
  titles: dict[str, dict[str, list[str]]] = {}
  for row in analysis.obligations:
    act = row.act or ""
    bucket = titles.setdefault(
      act,
      {
        "covered": [],
        "partial": [],
        "missing": [],
        "undetermined": [],
        "conflict": [],
        "violation": [],
        "not_applicable": [],
      },
    )
    bucket.setdefault(row.status, []).append(row.title)
  return titles


def _ordered_acts(analysis: AnalysisResult) -> list[str]:
  seen = list(analysis.applicable_laws)
  extras = sorted(
    act for act in {row.act or "" for row in analysis.obligations} if act and act not in seen
  )
  return [act for act in seen + extras if act]


def _priority_gaps(
  obligations: list[ObligationFinding],
  penalties: list[PenaltyFinding],
) -> list[ObligationFinding]:
  scored = {row.obligation_id: row for row in penalties}
  ranked = [
    row
    for row in obligations
    if row.status in {"violation", "missing"}
    and row.status != "not_applicable"
    and (row.status == "violation" or row.obligation_id in scored)
  ]

  def sort_key(row: ObligationFinding) -> tuple[int, float, float]:
    pen = scored.get(row.obligation_id)
    amount = pen.amount_crore if pen is not None and pen.amount_crore is not None else -1.0
    years = pen.imprisonment_years if pen is not None and pen.imprisonment_years is not None else -1.0
    tier = 2 if row.status == "violation" else 1
    return (tier, amount, years)

  ranked.sort(key=sort_key, reverse=True)
  return ranked[:PRIORITY_GAPS_CAP]


def _verdict_notes(analysis: AnalysisResult) -> list[LawNote]:
  buckets = _by_law_counts(analysis)
  notes: list[LawNote] = []
  for act in _ordered_acts(analysis):
    verdict = verdict_sentence(act, buckets.get(act) or ReportCounts())
    themes = engine_themes(analysis, act)
    note = f"{verdict} Themes: {themes}." if themes else verdict
    notes.append(LawNote(act=act, note=note))
  return notes


def _compose_summary(board: str, qwen: str, counts: ReportCounts) -> str:
  text = _HOWEVER.sub("", qwen.strip(), count=1).strip()
  text = _FRAMEWORK.sub("this policy", text).strip()
  if not text:
    return board
  first, rest = _first_sentence(text)
  if _has_scoreboard_counts(first, counts):
    if "this policy" not in first.lower():
      first = f"This policy: {first[0].lower() + first[1:]}" if first else board
    return " ".join(part for part in (first, rest) if part).strip()
  return f"{board} {text}".strip()


def _first_sentence(text: str) -> tuple[str, str]:
  parts = _SENTENCE.split(text.strip(), maxsplit=1)
  if len(parts) == 1:
    return parts[0].strip(), ""
  return parts[0].strip(), parts[1].strip()


def _has_scoreboard_counts(sentence: str, counts: ReportCounts) -> bool:
  return all(
    str(value) in sentence
    for value in (counts.covered, counts.partial, counts.missing, counts.total)
  )


def _now_iso() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_json(text: str) -> dict:
  cleaned = _FENCE.sub("", str(text).strip()).strip()
  data = json.loads(cleaned)
  if not isinstance(data, dict):
    raise ReportError("report JSON must be an object")
  return data


def _persist(report: ComplianceReport, document_id: str, report_dir: Path | None) -> None:
  target = report_dir if report_dir is not None else _env_report_dir()
  if target is None:
    return
  target.mkdir(parents=True, exist_ok=True)
  (target / f"{document_id}.json").write_text(
    report.model_dump_json(indent=2),
    encoding="utf-8",
  )


def _env_report_dir() -> Path | None:
  raw = os.environ.get("POLARIS_REPORT_DIR", "").strip()
  if not raw:
    return None
  return Path(raw)
