import { useState } from "react";

function fmt(value) {
  return Number(value || 0).toLocaleString();
}

function overlayCards(summary) {
  const coverage =
    summary.topics > 0 ? ((summary.covered / summary.topics) * 100).toFixed(1) : "0.0";
  return [
    {
      key: "nodes",
      label: "Nodes",
      value: fmt(summary.nodes),
      hint: "User graph entities",
    },
    {
      key: "edges",
      label: "Edges",
      value: fmt(summary.edges),
      hint: "User graph relationships",
    },
    {
      key: "coverage",
      label: "Coverage",
      value: `${coverage}%`,
      hint: "Keyword overlay topics",
      tone: "primary",
    },
    {
      key: "correct",
      label: "Correct",
      value: fmt(summary.covered),
      hint: "Matching topics",
      tone: "match",
      icon: "check_circle",
    },
    {
      key: "missing",
      label: "Missing",
      value: fmt(summary.missing),
      hint: "Topics with no keyword hit",
      tone: "error",
      icon: "cancel",
    },
    {
      key: "unexpected",
      label: "Unexpected",
      value: fmt(summary.extra),
      hint: "Extra policy sections",
      tone: "warn",
      icon: "add_circle",
    },
    {
      key: "conflicts",
      label: "Conflicts",
      value: fmt(summary.weak),
      hint: "Weak topic matches",
      tone: "conflict",
      icon: "warning",
    },
  ];
}

function engineCards(summary, analysis) {
  const obligations = analysis.obligations || [];
  const applicable = obligations.filter((row) => row.status !== "not_applicable");
  const covered = obligations.filter((row) => row.status === "covered").length;
  const partial = obligations.filter((row) => row.status === "partial").length;
  const missing = obligations.filter((row) => row.status === "missing").length;
  const na = obligations.filter((row) => row.status === "not_applicable").length;
  const violation = obligations.filter((row) => row.status === "violation").length;
  const conflict = obligations.filter((row) => row.status === "conflict").length;
  const undetermined = obligations.filter((row) => row.status === "undetermined").length;
  const catalog = obligations.length;
  const total = applicable.length;
  const coverage = total > 0 ? ((covered / total) * 100).toFixed(1) : "0.0";
  const weighted = analysis.weighted_pct;
  const gaps = analysis.gaps?.length ?? partial + missing + violation + conflict + undetermined;
  const adverse = violation + conflict;
  const coverageHint =
    adverse > 0
      ? `${violation} violation + ${conflict} conflict among ${total} applicable (${na} N/A of ${catalog} catalog)`
      : `${covered}/${total} applicable (${na} N/A of ${catalog} catalog)`;
  return [
    {
      key: "nodes",
      label: "Nodes",
      value: fmt(summary.nodes),
      hint: "User graph entities",
    },
    {
      key: "edges",
      label: "Edges",
      value: fmt(summary.edges),
      hint: "User graph relationships",
    },
    {
      key: "coverage",
      label: adverse > 0 ? "Adverse" : "Coverage",
      value: adverse > 0 ? fmt(adverse) : `${coverage}%`,
      hint: coverageHint,
      tone: adverse > 0 ? "error" : "primary",
    },
    {
      key: "weighted",
      label: "Weighted",
      value: `${weighted != null ? Number(weighted).toFixed(1) : coverage}%`,
      hint: "Severity-weighted applicable coverage",
      tone: "primary",
    },
    {
      key: "violation",
      label: "Violations",
      value: fmt(violation),
      hint: "Adverse policy language",
      tone: "error",
      icon: "report",
    },
    {
      key: "conflict",
      label: "Conflict",
      value: fmt(conflict),
      hint: "Supportive clause and a contradiction cue",
      tone: "conflict",
      icon: "warning",
    },
    {
      key: "correct",
      label: "Covered",
      value: fmt(covered),
      hint: "Obligations matched",
      tone: "match",
      icon: "check_circle",
    },
    {
      key: "partial",
      label: "Partial",
      value: fmt(partial),
      hint: "Weak or incomplete evidence",
      tone: "conflict",
      icon: "warning",
    },
    {
      key: "missing",
      label: "Missing",
      value: fmt(missing),
      hint: "No policy evidence (not a violation)",
      tone: "error",
      icon: "cancel",
    },
    {
      key: "na",
      label: "N/A",
      value: fmt(na),
      hint: `${na} not applicable of ${catalog} catalog duties`,
    },
    {
      key: "gaps",
      label: "Gaps",
      value: fmt(gaps),
      hint: "Partial + missing + violation + conflict",
      tone: "error",
      icon: "report",
    },
  ];
}

export default function CoverageStrip({ summary, analysis }) {
  const [collapsed, setCollapsed] = useState(false);
  const cards = analysis ? engineCards(summary, analysis) : overlayCards(summary);

  const highlightKeys = ["nodes", "edges", "coverage", "correct", "gaps", "violation"];
  const collapsedChips = cards.filter((c) => highlightKeys.includes(c.key));

  return (
    <div className={`metrics-strip-wrapper${collapsed ? " is-collapsed" : ""}`}>
      <div
        className="metrics-toggle-bar"
        role="button"
        tabIndex={0}
        onClick={() => setCollapsed((prev) => !prev)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setCollapsed((prev) => !prev);
          }
        }}
        aria-expanded={!collapsed}
        title={collapsed ? "Click to expand metrics" : "Click to collapse metrics"}
      >
        <div className="metrics-toggle-left">
          <span className="material-symbols-outlined metrics-toggle-icon">analytics</span>
          <span className="metrics-toggle-title">Metrics Overview</span>
          {collapsed && (
            <div className="metrics-collapsed-chips">
              {collapsedChips.map((chip) => (
                <span className="metrics-chip" key={chip.key}>
                  <span className="metrics-chip-label">{chip.label}:</span>
                  <span className={`metrics-chip-value${chip.tone ? ` tone-${chip.tone}` : ""}`}>
                    {chip.value}
                  </span>
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="metrics-toggle-right">
          <span className="metrics-toggle-text">{collapsed ? "Expand" : "Collapse"}</span>
          <span className="material-symbols-outlined metrics-chevron">
            {collapsed ? "expand_more" : "expand_less"}
          </span>
        </div>
      </div>

      {!collapsed && (
        <div className="metrics-bar">
          {cards.map((card) => (
            <div className="metric-card" key={card.key}>
              <span className={`metric-label${card.tone ? ` tone-${card.tone}` : ""}`}>
                {card.icon ? (
                  <span className="material-symbols-outlined metric-icon">{card.icon}</span>
                ) : null}
                {card.label}
              </span>
              <span className={`metric-value${card.tone ? ` tone-${card.tone}` : ""}`}>{card.value}</span>
              <span className="metric-hint">{card.hint}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
