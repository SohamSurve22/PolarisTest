import { useState } from "react";
import { countsBanner } from "./countsBanner";
import { primaryMatch } from "./closestCitation";

const FILTERS = [
  { id: "gaps", label: "Gaps" },
  { id: "violation", label: "Violation" },
  { id: "missing", label: "Missing" },
  { id: "partial", label: "Partial" },
  { id: "covered", label: "Covered" },
  { id: "not_applicable", label: "N/A" },
  { id: "undetermined", label: "Undetermined" },
  { id: "conflict", label: "Conflict" },
  { id: "all", label: "All" },
];

const BADGE = {
  covered: { label: "COVERED", className: "badge-match" },
  partial: { label: "PARTIAL", className: "badge-partial" },
  missing: { label: "MISSING", className: "badge-missing" },
  not_applicable: { label: "N/A", className: "badge-na" },
  undetermined: { label: "UNDETERMINED", className: "badge-undetermined" },
  violation: { label: "VIOLATION", className: "badge-violation" },
  conflict: { label: "CONFLICT", className: "badge-conflict" },
};

function matchesFilter(row, filter) {
  if (filter === "all") {
    return true;
  }
  if (filter === "gaps") {
    return ["missing", "partial", "undetermined", "conflict", "violation"].includes(row.status);
  }
  return row.status === filter;
}

function policyMap(row) {
  const first = primaryMatch(row);
  const counter = (row.counter_evidence || [])[0];
  const matches = row.matched_clauses || [];
  if (!first) {
    if (row.evidence_quality === "NO_RELIABLE_MATCH") {
      return {
        heading: "No reliable evidence found",
        text: "The closest clause was below the relevance threshold.",
        extra: 0,
        counter: "",
      };
    }
    return {
      heading: "No matching clause",
      text: "Nothing in this policy maps to this duty.",
      extra: 0,
      counter: "",
    };
  }
  return {
    heading: first.section_title || first.clause_id,
    text: first.text,
    extra: Math.max(0, matches.length - (row.status === "violation" || row.status === "conflict" ? 0 : 1)),
    counter:
      row.status === "violation" || row.status === "conflict"
        ? ""
        : counter && counter !== first
          ? counter.text
          : "",
  };
}

function elementMark(item) {
  const result = item.result || (item.satisfied ? "supported" : "absent");
  if (result === "supported") {
    return { className: "el-yes", mark: "✓" };
  }
  if (result === "contradicted") {
    return { className: "el-contra", mark: "✗" };
  }
  return { className: "el-no", mark: "○" };
}

const GAP_RANK = { violation: 0, conflict: 1, missing: 2, undetermined: 3, partial: 4 };

function statute(row) {
  const act = String(row.act || "").trim();
  const title = String(row.title || "").trim();
  if (act && title) {
    return `${act}: ${title}`;
  }
  return title || act || row.obligation_id;
}

function why(row) {
  if (row.reason) {
    return row.reason;
  }
  if (row.status === "covered") {
    return `This clause satisfies ${statute(row)}.`;
  }
  if (row.status === "partial") {
    return `Closest policy text is related, but it does not clearly cover ${statute(row)}.`;
  }
  if (row.status === "not_applicable") {
    return row.applicability_reason || "This obligation does not apply.";
  }
  return "No clause in this policy maps to this duty. Missing policy language is not a finding of legal violation.";
}

export function policyNodeForClause(policyGraph, clauseId) {
  if (!clauseId || !policyGraph?.nodes) {
    return null;
  }
  const sectionId = String(clauseId).split("_C")[0];
  return (
    policyGraph.nodes.find((node) => {
      if (node.kind !== "section") {
        return false;
      }
      const sid = node.extra?.section_id || String(node.id).replace(/^section:/, "");
      return sid === sectionId;
    }) || null
  );
}

export function activeFindingIds(selected, analysis) {
  const ids = new Set();
  if (!selected || !analysis?.obligations) {
    return ids;
  }
  if (selected.kind === "law_chunk") {
    ids.add(selected.id);
    return ids;
  }
  if (selected.kind === "section") {
    const sid = selected.extra?.section_id || String(selected.id).replace(/^section:/, "");
    for (const row of analysis.obligations) {
      const hit = (row.matched_clause_ids || []).some(
        (clauseId) => String(clauseId).split("_C")[0] === sid,
      );
      if (hit) {
        ids.add(row.obligation_id);
      }
    }
  }
  return ids;
}

export default function Findings({
  analysis,
  analysisError,
  busy,
  selected,
  onSelectFinding,
  report,
  reportError,
  reportBusy,
  onViewReport,
}) {
  const [filter, setFilter] = useState("gaps");
  const obligations = analysis?.obligations || [];
  const counts = {
    gaps: obligations.filter((row) =>
      ["missing", "partial", "undetermined", "conflict", "violation"].includes(row.status),
    ).length,
    missing: obligations.filter((row) => row.status === "missing").length,
    partial: obligations.filter((row) => row.status === "partial").length,
    covered: obligations.filter((row) => row.status === "covered").length,
    not_applicable: obligations.filter((row) => row.status === "not_applicable").length,
    undetermined: obligations.filter((row) => row.status === "undetermined").length,
    violation: obligations.filter((row) => row.status === "violation").length,
    conflict: obligations.filter((row) => row.status === "conflict").length,
    all: obligations.length,
  };
  const rows = obligations
    .filter((row) => matchesFilter(row, filter))
    .slice()
    .sort((a, b) => (GAP_RANK[a.status] ?? 9) - (GAP_RANK[b.status] ?? 9));
  const applicable = counts.all - counts.not_applicable;
  const active = activeFindingIds(selected, analysis);
  const penaltiesByOid = new Map();
  for (const pen of analysis?.penalties || []) {
    const list = penaltiesByOid.get(pen.obligation_id) || [];
    list.push(pen);
    penaltiesByOid.set(pen.obligation_id, list);
  }

  return (
    <section className="findings" aria-label="Obligation findings">
      <div className="findings-head">
        <div>
          <h2>Findings</h2>
          <p>
            {analysis
              ? `${analysis.jurisdiction}${
                  analysis.applicable_laws?.length ? ` · ${analysis.applicable_laws.join(", ")}` : ""
                } · click a row to highlight the law and policy nodes`
              : "Maps each law to the closest clause in this policy"}
          </p>
        </div>
        {analysis ? (
          <p className="findings-stat">
            {countsBanner({
              covered: counts.covered,
              partial: counts.partial,
              missing: counts.missing,
              violation: counts.violation,
              conflict: counts.conflict,
              not_applicable: counts.not_applicable,
              undetermined: counts.undetermined,
            })}
          </p>
        ) : null}
      </div>

      {analysisError && !analysis ? (
        <p className="findings-empty">{analysisError}</p>
      ) : !analysis ? (
        <p className="findings-empty">
          {busy ? "Scoring obligations against Indian website-privacy law…" : "Run validation to score obligations."}
        </p>
      ) : (
        <>
          <div className="findings-filters" role="tablist" aria-label="Filter findings">
            {FILTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={filter === item.id}
                className={`findings-filter${filter === item.id ? " is-active" : ""}`}
                onClick={() => setFilter(item.id)}
              >
                {item.label}
                <span>{counts[item.id]}</span>
              </button>
            ))}
          </div>
          {rows.length ? (
            <div className="findings-table-wrap">
              <div className="findings-grid" role="table">
                <div className="findings-row findings-row--head" role="row">
                  <div role="columnheader">Status</div>
                  <div role="columnheader">Law</div>
                  <div role="columnheader">Duty</div>
                  <div role="columnheader">In this policy</div>
                  <div role="columnheader">Why</div>
                </div>
                {rows.map((row) => {
                  const mapped = policyMap(row);
                  const badge = BADGE[row.status] || BADGE.missing;
                  const pens = penaltiesByOid.get(row.obligation_id) || [];
                  return (
                    <div
                      key={row.obligation_id}
                      className={`findings-row${active.has(row.obligation_id) ? " is-active" : ""}`}
                      role="row"
                      tabIndex={0}
                      onClick={() => onSelectFinding(row)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelectFinding(row);
                        }
                      }}
                    >
                      <div role="cell">
                        <span className={`mono-badge ${badge.className}`}>{badge.label}</span>
                      </div>
                      <div className="findings-act" role="cell">
                        {row.act || "—"}
                      </div>
                      <div role="cell">
                        <div className="findings-duty">{row.title}</div>
                        {pens.length ? (
                          <div className="findings-risk">
                            {pens
                              .map((pen) => {
                                const amount =
                                  pen.amount_crore != null ? `₹${pen.amount_crore} crore` : "";
                                const eligibility = pen.eligibility || "potential_exposure";
                                return `${pen.title}${amount ? ` · ${amount}` : ""} · ${eligibility}`;
                              })
                              .join(" · ")}
                            <div className="findings-disclaimer">
                              Not a determination of liability.
                            </div>
                          </div>
                        ) : null}
                        {(row.elements || []).length ? (
                          <div className="findings-elements">
                            {(row.elements || []).map((item) => {
                              const mark = elementMark(item);
                              return (
                                <span key={item.id} className={mark.className}>
                                  {mark.mark} {item.label}
                                </span>
                              );
                            })}
                          </div>
                        ) : null}
                      </div>
                      <div role="cell">
                        <div className="findings-clause">{mapped.heading}</div>
                        <div className="findings-snippet">{mapped.text}</div>
                        {mapped.counter ? (
                          <div className="findings-counter">
                            Counter-evidence: {mapped.counter}
                          </div>
                        ) : null}
                        {mapped.extra > 0 ? (
                          <div className="findings-more">
                            +{mapped.extra} more clause{mapped.extra === 1 ? "" : "s"}
                          </div>
                        ) : null}
                      </div>
                      <div className="findings-why" role="cell">
                        {why(row)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <p className="findings-empty">No obligations in this filter.</p>
          )}
          {reportBusy || reportError || report ? (
            <div className="findings-foot">
              {reportBusy ? (
                <p className="findings-memo-status">Writing memo (local Qwen)…</p>
              ) : null}
              {reportError && !report ? <p className="findings-memo-status">{reportError}</p> : null}
              {report ? (
                <button className="btn-secondary" type="button" onClick={onViewReport}>
                  View Report
                </button>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
