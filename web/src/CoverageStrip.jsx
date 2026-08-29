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
  const covered = obligations.filter((row) => row.status === "covered").length;
  const partial = obligations.filter((row) => row.status === "partial").length;
  const missing = obligations.filter((row) => row.status === "missing").length;
  const total = obligations.length;
  const coverage = total > 0 ? ((covered / total) * 100).toFixed(1) : "0.0";
  const gaps = analysis.gaps?.length ?? partial + missing;
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
      hint: `${covered}/${total} obligations`,
      tone: "primary",
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
      hint: "Weak or title-mismatch",
      tone: "conflict",
      icon: "warning",
    },
    {
      key: "missing",
      label: "Missing",
      value: fmt(missing),
      hint: "No matching clause",
      tone: "error",
      icon: "cancel",
    },
    {
      key: "gaps",
      label: "Gaps",
      value: fmt(gaps),
      hint: "Partial + missing",
      tone: "error",
      icon: "report",
    },
  ];
}

export default function CoverageStrip({ summary, analysis }) {
  const cards = analysis ? engineCards(summary, analysis) : overlayCards(summary);

  return (
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
  );
}
