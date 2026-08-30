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
  ReportCounts,
)

ChatFn = Callable[[str, str], str]

DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
NARRATIVE_UNAVAILABLE = "Narrative unavailable. The table below is from automated analysis only."

SYSTEM = """You write a short client-facing compliance memo from structured analysis JSON.
You must not invent laws, obligation ids, statuses, or penalties.
Statuses in the JSON are already final. Cover what is in place, what is partial, and what is missing.
Return only this object:
{"executive_summary": string, "law_notes": [{"act": string, "note": string}]}
executive_summary under 160 words. Each law note under 60 words. Use only acts listed in applicable_laws.
"""

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
          "note": {"type": "string"},
        },
        "required": ["act", "note"],
      },
    },
  },
  "required": ["executive_summary", "law_notes"],
}


class ReportError(Exception):
  """Chat model unavailable or returned unusable JSON."""


def compact_payload(analysis: AnalysisResult) -> dict:
  counts = _counts(analysis)
  by_act: dict[str, dict[str, list[str]]] = {}
  for row in analysis.obligations:
    bucket = by_act.setdefault(row.act or "", {"covered": [], "partial": [], "missing": []})
    bucket[row.status].append(row.title)
  ordered_acts = list(analysis.applicable_laws)
  for act in sorted(key for key in by_act if key not in ordered_acts):
    ordered_acts.append(act)
  by_law = []
  for act in ordered_acts:
    titles = by_act.get(act) or {"covered": [], "partial": [], "missing": []}
    by_law.append(
      {
        "act": act,
        "covered": titles["covered"],
        "partial": titles["partial"],
        "missing": titles["missing"],
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
    jurisdiction=analysis.jurisdiction,
    applicable_laws=list(analysis.applicable_laws),
    generated_at=generated_at,
    model=model,
    counts=counts,
    findings=list(analysis.obligations),
    penalties=penalties,
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

  allowed_acts = set(analysis.applicable_laws)
  notes: list[LawNote] = []
  for item in parsed.get("law_notes") or []:
    act = str(item.get("act") or "")
    if act not in allowed_acts:
      continue
    notes.append(LawNote(act=act, note=str(item.get("note") or "").strip()))
  report.executive_summary = summary
  report.narrative_available = True
  report.model = model_name
  report.law_notes = notes
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


def _counts(analysis: AnalysisResult) -> ReportCounts:
  covered = sum(1 for row in analysis.obligations if row.status == "covered")
  partial = sum(1 for row in analysis.obligations if row.status == "partial")
  missing = sum(1 for row in analysis.obligations if row.status == "missing")
  return ReportCounts(
    covered=covered,
    partial=partial,
    missing=missing,
    total=len(analysis.obligations),
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
