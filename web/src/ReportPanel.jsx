import { useState } from "react";
import { countsBanner } from "./countsBanner";
import { primaryMatch } from "./closestCitation";

const NARRATIVE_UNAVAILABLE = "Narrative unavailable. The table below is from automated analysis only.";

const BADGE = {
  covered: "badge-match",
  partial: "badge-partial",
  missing: "badge-missing",
  not_applicable: "badge-na",
  undetermined: "badge-undetermined",
  violation: "badge-violation",
  conflict: "badge-conflict",
};

function closest(row) {
  const first = primaryMatch(row);
  if (!first) {
    return {
      heading: row.evidence_quality === "NO_RELIABLE_MATCH" ? "No reliable evidence found" : "No matching clause",
      text: "",
      counter: "",
    };
  }
  const extra =
    row.status === "violation" || row.status === "conflict"
      ? ""
      : (row.counter_evidence || [])[0] && (row.counter_evidence || [])[0] !== first
        ? (row.counter_evidence || [])[0].text || ""
        : "";
  return {
    heading: first.section_title || first.clause_id || "Clause",
    text: first.text || "",
    counter: extra,
  };
}

function displaySourceName(report) {
  const raw = String(report.source_filename || "").trim().replace(/\\/g, "/");
  const base = (raw.split("/").pop() || "").replace(/[/\\"]/g, "_").trim();
  return base || report.document_id || "";
}

function pdfDownloadName(report) {
  const shown = displaySourceName(report);
  const stem = shown.replace(/\.[^.]+$/, "") || report.document_id || "report";
  const safe = String(stem).replace(/[/\\"]/g, "_").trim() || report.document_id || "report";
  return `polarislex-${safe}.pdf`;
}

function exposure(row, penalties) {
  const pen = (penalties || []).find((item) => item.obligation_id === row.obligation_id);
  if (!pen) {
    return "";
  }
  const parts = [];
  if (pen.amount_crore != null && pen.amount_crore !== "") {
    parts.push(`₹${pen.amount_crore} crore`);
  }
  if (pen.imprisonment_years != null && pen.imprisonment_years !== "") {
    parts.push(`${pen.imprisonment_years} years`);
  }
  return parts.join(", ");
}

function groupFindings(report) {
  const findings = report.findings || [];
  const laws = [...(report.applicable_laws || [])];
  const byAct = new Map();
  const rank = { violation: 0, conflict: 1, missing: 2, undetermined: 3, partial: 4, covered: 5, not_applicable: 6 };
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
    byAct.get(act).sort((a, b) => (rank[a.status] ?? 9) - (rank[b.status] ?? 9));
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

  const summary = String(report.executive_summary || "").trim() || NARRATIVE_UNAVAILABLE;
  const gaps = report.priority_gaps || [];

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
      link.download = pdfDownloadName(report);
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
      </div>
      {displaySourceName(report) ? <p className="report-file">{displaySourceName(report)}</p> : null}
      {report.counts ? <p className="report-counts">{countsBanner(report.counts)}</p> : null}
      <p className="report-summary">{summary}</p>
      {gaps.length ? (
        <section className="report-gaps" aria-label="Priority gaps">
          <h4>Priority gaps</h4>
          <ul>
            {gaps.map((row) => (
              <li key={row.obligation_id}>
                <span className="report-gap-title">{row.title}</span>
                {row.act ? <span className="report-gap-act"> {row.act}</span> : null}
                {exposure(row, report.penalties) ? (
                  <span className="report-gap-exposure"> — {exposure(row, report.penalties)} (potential exposure)</span>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
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
                  {match.counter ? (
                    <p className="report-duty-counter">Counter-evidence: {match.counter}</p>
                  ) : null}
                </div>
              </div>
            );
          })}
        </section>
      ))}
      <p className="report-caveat">{report.caveats}</p>
      <div className="report-actions">
        <button type="button" className="btn-secondary" onClick={downloadPdf} disabled={downloading}>
          {downloading ? "Preparing PDF…" : "Download PDF"}
        </button>
        {dlError ? <p className="findings-empty">{dlError}</p> : null}
      </div>
    </section>
  );
}
