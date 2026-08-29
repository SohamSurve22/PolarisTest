function fmt(value) {
  return Number(value || 0).toLocaleString();
}

export default function CoverageStrip({ summary }) {
  const coverage =
    summary.topics > 0 ? ((summary.covered / summary.topics) * 100).toFixed(1) : "0.0";
  const cards = [
    {
      key: "nodes",
      label: "Nodes",
      value: fmt(summary.nodes),
      hint: "Total entities parsed",
    },
    {
      key: "edges",
      label: "Edges",
      value: fmt(summary.edges),
      hint: "Total relationships",
    },
    {
      key: "coverage",
      label: "Coverage",
      value: `${coverage}%`,
      hint: "Against ideal graph",
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
      hint: "Absent in user graph",
      tone: "error",
      icon: "cancel",
    },
    {
      key: "unexpected",
      label: "Unexpected",
      value: fmt(summary.extra),
      hint: "Extra nodes found",
      tone: "warn",
      icon: "add_circle",
    },
    {
      key: "conflicts",
      label: "Conflicts",
      value: fmt(summary.weak),
      hint: "Partial / weak matches",
      tone: "conflict",
      icon: "warning",
    },
  ];

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
