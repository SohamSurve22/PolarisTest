from compliance.models import (
  ComplianceReport,
  LawNote,
  ObligationFinding,
  PenaltyFinding,
  ReportCounts,
)
from compliance.pdf import render_pdf
from compliance.report import NARRATIVE_UNAVAILABLE


def _report() -> ComplianceReport:
  return ComplianceReport(
    document_id="DOC_x",
    jurisdiction="IN",
    applicable_laws=["TINY"],
    generated_at="2026-08-30T05:00:00Z",
    counts=ReportCounts(covered=1, partial=0, missing=1, total=2),
    executive_summary="",
    narrative_available=False,
    law_notes=[LawNote(act="TINY", note="Security is missing.")],
    findings=[
      ObligationFinding(
        obligation_id="TINY_CONSENT",
        title="Obtain consent",
        act="TINY",
        status="covered",
      ),
      ObligationFinding(
        obligation_id="TINY_SECURE",
        title="Secure personal data",
        act="TINY",
        status="missing",
      ),
    ],
    penalties=[
      PenaltyFinding(
        obligation_id="TINY_SECURE",
        title="Fine for insecure processing",
        amount_crore=250,
        act="TINY",
      ),
    ],
  )


def test_render_pdf_contains_all_obligation_ids() -> None:
  pdf = render_pdf(_report())
  assert pdf.startswith(b"%PDF")
  assert b"TINY_CONSENT" in pdf
  assert b"TINY_SECURE" in pdf
  assert b"PolarisLex" in pdf
  assert NARRATIVE_UNAVAILABLE.encode("latin-1") in pdf
  assert b"Not a legal opinion. Coverage statuses are from automated analysis" in pdf
