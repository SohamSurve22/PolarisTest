import { useState } from "react";

const NARRATIVE_UNAVAILABLE = "Narrative unavailable. The table below is from automated analysis only.";

const BADGE = {
  covered: "badge-match",
  partial: "badge-partial",
  missing: "badge-missing",
};

function clip(text, limit = 180) {
  const value = String(text || "").replace(/\s+/g, " ").trim();
  if (value.length <= limit) {
    return value;
  }
  return `${value.slice(0, limit).trim()}…`;
}

function closest(row) {
  const matches = row.matched_clauses || [];
  if (!matches.length) {
    return { heading: "No matching clause", text: "" };
  }
  const first = matches[0];
  return {
    heading: first.section_title || first.clause_id || "Clause",
    text: clip(first.text),
  };
}

function groupFindings(report) {
  const findings = report.findings || [];
  const laws = [...(report.applicable_laws || [])];
  const byAct = new Map();
  for (const row of findings) {
    const act = row.act || "Other";
    if (!byAct.has(act)) {
      byAct.set(act, []);
    }
    byAct.get(act).push(row);
  }
  for (const act of byAct.keys()) {
    if (!laws.includes(act)) {
      laws.push(act);
    }
  }
  const notes = Object.fromEntries((report.law_notes || []).map((item) => [item.act, item.note]));
  return laws.map((act) => ({
    act: act || "Other",
    note: notes[act] || "",
    rows: byAct.get(act) || [],
  }));
}

export default function ReportPanel({ report, reportError, busy }) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState("");

  if (reportError && !report) {
    return (
      <section className="report-panel" aria-label="Compliance report">
        <h3>Report</h3>
        <p className="findings-empty">{reportError}</p>
      </section>
    );
  }
  if (!report && busy) {
    return (
      <section className="report-panel" aria-label="Compliance report">
        <h3>Report</h3>
        <p className="findings-empty">Writing a memo from the findings (local Qwen). This can take up to a minute…</p>
      </section>
    );
  }
  if (!report) {
    return null;
  }

  const counts = report.counts || {};
  const summary = report.narrative_available
    ? report.executive_summary
    : NARRATIVE_UNAVAILABLE;

  async function downloadPdf() {
    setDlError("");
    setDownloading(true);
    try {
      const response = await fetch("/api/report.pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(report),
      });
      if (!response.ok) {
        throw new Error("PDF download failed");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `polarislex-${report.document_id}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setDlError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <section className="report-panel" aria-label="Compliance report">
      <div className="report-head">
        <h3>Report</h3>
        <button type="button" className="btn-secondary" onClick={downloadPdf} disabled={downloading}>
          {downloading ? "Preparing PDF…" : "Download PDF"}
        </button>
      </div>
      <p className="report-counts">
        Covered {counts.covered ?? 0} · Partial {counts.partial ?? 0} · Missing {counts.missing ?? 0} · Total{" "}
        {counts.total ?? 0}
      </p>
      <p className="report-summary">{summary}</p>
      {groupFindings(report).map((section) => (
        <section key={section.act} className="report-law">
          <h4>{section.act}</h4>
          {section.note ? <p className="report-law-note">{section.note}</p> : null}
          {section.rows.map((row) => {
            const match = closest(row);
            return (
              <div key={row.obligation_id} className="report-duty">
                <span className={`mono-badge ${BADGE[row.status] || "badge-missing"}`}>
                  {String(row.status || "").toUpperCase()}
                </span>
                <div>
                  <p className="report-duty-title">{row.title}</p>
                  <p className="report-duty-id">{row.obligation_id}</p>
                  <p className="report-duty-clause">
                    {match.heading}
                    {match.text ? ` — ${match.text}` : ""}
                  </p>
                </div>
              </div>
            );
          })}
        </section>
      ))}
      {dlError ? <p className="findings-empty">{dlError}</p> : null}
      <p className="report-caveat">{report.caveats}</p>
    </section>
  );
}
