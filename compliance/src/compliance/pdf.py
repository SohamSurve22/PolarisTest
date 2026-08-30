"""Deterministic client memo PDF from ComplianceReport. No LLM."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from compliance.models import ComplianceReport, ObligationFinding
from compliance.report import NARRATIVE_UNAVAILABLE

FOOTER = (
  "Not a legal opinion. Coverage statuses are from automated analysis, not the language model. "
  "Missing policy language is not a finding of legal violation."
)
_SNIPPET = 180
_STATUS = {
  "covered": "COVERED",
  "partial": "PARTIAL",
  "missing": "MISSING",
  "not_applicable": "NOT APPLICABLE",
  "undetermined": "UNDETERMINED",
  "conflict": "CONFLICT",
  "violation": "VIOLATION",
}
_UNSAFE = re.compile(r'[/\\"\r\n]+')


def display_source_name(report: ComplianceReport) -> str:
  raw = str(report.source_filename or "").strip().replace("\\", "/")
  name = _UNSAFE.sub("_", Path(raw).name).strip()
  return name or report.document_id


def pdf_download_name(report: ComplianceReport) -> str:
  display = display_source_name(report)
  stem = _UNSAFE.sub("_", Path(display).stem).strip() or report.document_id
  return f"polarislex-{stem}.pdf"


def render_pdf(report: ComplianceReport) -> bytes:
  buffer = BytesIO()
  shown = display_source_name(report)
  doc = SimpleDocTemplate(
    buffer,
    pagesize=A4,
    leftMargin=18 * mm,
    rightMargin=18 * mm,
    topMargin=22 * mm,
    bottomMargin=20 * mm,
    title=f"PolarisLex {shown}",
    author="PolarisLex",
    pageCompression=0,
  )
  styles = _styles()
  story: list = []
  story.append(Paragraph("PolarisLex", styles["title"]))
  story.append(Paragraph("Compliance memorandum", styles["sub"]))
  story.append(Spacer(1, 6 * mm))
  story.append(Paragraph(_esc(f"Document: {shown}"), styles["body"]))
  if report.generated_at:
    story.append(Paragraph(_esc(f"Generated: {report.generated_at}"), styles["body"]))
  if report.jurisdiction:
    story.append(Paragraph(_esc(f"Jurisdiction: {report.jurisdiction}"), styles["body"]))
  if report.applicable_laws:
    story.append(Paragraph(_esc("Laws: " + ", ".join(report.applicable_laws)), styles["body"]))
  counts = report.counts
  story.append(
    Paragraph(
      _esc(
        f"Covered {counts.covered} · Partial {counts.partial} · "
        f"Missing {counts.missing} · N/A {counts.not_applicable} · Total {counts.total}"
      ),
      styles["counts"],
    )
  )
  story.append(Spacer(1, 4 * mm))
  story.append(Paragraph("Executive summary", styles["h"]))
  summary = (report.executive_summary or "").strip()
  story.append(Paragraph(_esc(summary or NARRATIVE_UNAVAILABLE), styles["body"]))
  _priority_gap_block(story, report, styles)

  notes = {row.act: row.note for row in report.law_notes}
  grouped: dict[str, list[ObligationFinding]] = {}
  for row in report.findings:
    grouped.setdefault(row.act or "Other", []).append(row)
  acts = list(report.applicable_laws)
  for act in grouped:
    if act not in acts:
      acts.append(act)

  for act in acts:
    rows = grouped.get(act) or []
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(_esc(act or "Other"), styles["h"]))
    note = notes.get(act, "")
    if note:
      story.append(Paragraph(_esc(note), styles["body"]))
    if rows:
      story.append(_duty_table(rows, styles))

  if report.penalties:
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Potential statutory exposure", styles["h"]))
    for row in report.penalties:
      amount = f"{row.amount_crore} crore" if row.amount_crore is not None else ""
      years = f"{row.imprisonment_years} years" if row.imprisonment_years is not None else ""
      extra = ", ".join(part for part in (amount, years) if part)
      label = f"{row.obligation_id}: {row.title}"
      if extra:
        label = f"{label} ({extra})"
      if row.eligibility:
        label = f"{label} [{row.eligibility}]"
      if row.reason:
        label = f"{label} — {row.reason}"
      story.append(Paragraph(_esc(label), styles["body"]))

  story.append(Spacer(1, 6 * mm))
  story.append(Paragraph(_esc(report.caveats), styles["small"]))

  def _chrome(canvas, _doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, A4[1] - 14 * mm, f"PolarisLex  {shown}")
    canvas.drawString(18 * mm, 10 * mm, FOOTER)
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(_doc.page))
    canvas.restoreState()

  doc.build(story, onFirstPage=_chrome, onLaterPages=_chrome)
  return buffer.getvalue()


def _priority_gap_block(story: list, report: ComplianceReport, styles: dict) -> None:
  if not report.priority_gaps:
    return
  by_id = {row.obligation_id: row for row in report.penalties}
  story.append(Spacer(1, 4 * mm))
  story.append(Paragraph("Priority gaps", styles["h"]))
  for row in report.priority_gaps:
    extra = _exposure(by_id.get(row.obligation_id))
    label = f"{row.obligation_id}: {row.title} ({row.act or 'Other'})"
    if extra:
      label = f"{label} — {extra}"
    story.append(Paragraph(_esc(label), styles["body"]))


def _exposure(penalty) -> str:
  if penalty is None:
    return ""
  amount = f"{penalty.amount_crore} crore" if penalty.amount_crore is not None else ""
  years = f"{penalty.imprisonment_years} years" if penalty.imprisonment_years is not None else ""
  return ", ".join(part for part in (amount, years) if part)


def _duty_table(rows: list[ObligationFinding], styles: dict) -> Table:
  header = [
    Paragraph("Status", styles["th"]),
    Paragraph("Duty", styles["th"]),
    Paragraph("Id", styles["th"]),
    Paragraph("Closest clause", styles["th"]),
  ]
  data = [header]
  for row in rows:
    data.append(
      [
        Paragraph(_esc(_STATUS.get(row.status, row.status.upper())), styles["td"]),
        Paragraph(_esc(row.title), styles["td"]),
        Paragraph(_esc(row.obligation_id), styles["td"]),
        Paragraph(_esc(_closest(row)), styles["td"]),
      ]
    )
  table = Table(data, colWidths=[28 * mm, 52 * mm, 38 * mm, 52 * mm], repeatRows=1)
  table.setStyle(
    TableStyle(
      [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.93, 0.94, 0.96)),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.7, 0.72, 0.75)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
      ]
    )
  )
  return table


def _closest(row: ObligationFinding) -> str:
  if row.evidence_quality == "NO_RELIABLE_MATCH" or not row.matched_clauses:
    if row.evidence_quality == "NO_RELIABLE_MATCH":
      return "No reliable evidence found"
    return "No matching clause"
  first = row.matched_clauses[0]
  heading = first.section_title or first.clause_id
  text = " ".join(str(first.text or "").split())
  if len(text) > _SNIPPET:
    text = f"{text[:_SNIPPET].rstrip()}..."
  if heading and text:
    return f"{heading}: {text}"
  return heading or text or "No matching clause"


def _styles() -> dict:
  base = getSampleStyleSheet()
  return {
    "title": ParagraphStyle(
      "PolarisTitle",
      parent=base["Heading1"],
      fontName="Helvetica-Bold",
      fontSize=16,
      leading=20,
      alignment=TA_LEFT,
      spaceAfter=2,
    ),
    "sub": ParagraphStyle(
      "PolarisSub",
      parent=base["Normal"],
      fontName="Helvetica",
      fontSize=10,
      textColor=colors.Color(0.3, 0.32, 0.36),
      spaceAfter=4,
    ),
    "h": ParagraphStyle(
      "PolarisH",
      parent=base["Heading2"],
      fontName="Helvetica-Bold",
      fontSize=11,
      leading=14,
      spaceBefore=4,
      spaceAfter=4,
    ),
    "body": ParagraphStyle(
      "PolarisBody",
      parent=base["Normal"],
      fontName="Helvetica",
      fontSize=9,
      leading=12,
      spaceAfter=3,
    ),
    "counts": ParagraphStyle(
      "PolarisCounts",
      parent=base["Normal"],
      fontName="Helvetica-Bold",
      fontSize=10,
      leading=13,
      spaceBefore=4,
      spaceAfter=4,
    ),
    "th": ParagraphStyle(
      "PolarisTh",
      parent=base["Normal"],
      fontName="Helvetica-Bold",
      fontSize=8,
      leading=10,
    ),
    "td": ParagraphStyle(
      "PolarisTd",
      parent=base["Normal"],
      fontName="Helvetica",
      fontSize=8,
      leading=10,
    ),
    "small": ParagraphStyle(
      "PolarisSmall",
      parent=base["Normal"],
      fontName="Helvetica",
      fontSize=8,
      leading=10,
      textColor=colors.Color(0.35, 0.37, 0.4),
    ),
  }


def _esc(text: str) -> str:
  return (
    str(text or "")
    .replace("&", "&amp;")
    .replace("<", "&lt;")
    .replace(">", "&gt;")
  )
