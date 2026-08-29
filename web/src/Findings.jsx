import { useState } from "react";

const FILTERS = [
  { id: "gaps", label: "Gaps" },
  { id: "missing", label: "Missing" },
  { id: "partial", label: "Partial" },
  { id: "covered", label: "Covered" },
  { id: "all", label: "All" },
];

const BADGE = {
  covered: { label: "COVERED", className: "badge-match" },
  partial: { label: "PARTIAL", className: "badge-partial" },
  missing: { label: "MISSING", className: "badge-missing" },
};

function clip(text, limit = 180) {
  const value = String(text || "").replace(/\s+/g, " ").trim();
  if (value.length <= limit) {
    return value;
  }
  return `${value.slice(0, limit).trim()}…`;
}

function matchesFilter(row, filter) {
  if (filter === "all") {
    return true;
  }
  if (filter === "gaps") {
    return row.status !== "covered";
  }
  return row.status === filter;
}

function policyMap(row) {
  const matches = row.matched_clauses || [];
  if (!matches.length) {
    const ids = row.matched_clause_ids || [];
    if (ids.length) {
      return {
        heading: ids[0],
        text: "Closest policy clause is linked, but the snippet was not returned.",
        extra: ids.length - 1,
      };
    }
    return {
      heading: "No matching clause",
      text: "Nothing in this policy maps to this duty.",
      extra: 0,
    };
  }
  const first = matches[0];
  return {
    heading: first.section_title || first.clause_id,
    text: clip(first.text),
    extra: matches.length - 1,
  };
}

function why(row) {
  if (row.status === "covered") {
    return "This policy section covers the duty.";
  }
  if (row.status === "partial") {
    return "Closest policy text is related, but it does not clearly cover this duty.";
  }
  return "No clause in this policy maps to this duty.";
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
}) {
  const [filter, setFilter] = useState("gaps");
  const obligations = analysis?.obligations || [];
  const counts = {
    gaps: obligations.filter((row) => row.status !== "covered").length,
    missing: obligations.filter((row) => row.status === "missing").length,
    partial: obligations.filter((row) => row.status === "partial").length,
    covered: obligations.filter((row) => row.status === "covered").length,
    all: obligations.length,
  };
  const rows = obligations.filter((row) => matchesFilter(row, filter));
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
            {counts.covered}/{counts.all} covered · {counts.gaps} gaps
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
                              .map((pen) =>
                                pen.amount_crore != null
                                  ? `${pen.title} · ₹${pen.amount_crore} crore`
                                  : pen.title,
                              )
                              .join(" · ")}
                          </div>
                        ) : null}
                      </div>
                      <div role="cell">
                        <div className="findings-clause">{mapped.heading}</div>
                        <div className="findings-snippet">{mapped.text}</div>
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
        </>
      )}
    </section>
  );
}
