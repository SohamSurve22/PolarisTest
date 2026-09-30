const STATUS_META = {
  covered: { label: "COVERED", icon: "check_circle", className: "nd-status-covered" },
  mapped: { label: "MATCH", icon: "check_circle", className: "nd-status-covered" },
  weak: { label: "PARTIAL", icon: "warning", className: "nd-status-weak" },
  partial: { label: "PARTIAL", icon: "warning", className: "nd-status-weak" },
  missing: { label: "MISSING", icon: "cancel", className: "nd-status-missing" },
  extra: { label: "EXTRA", icon: "add_circle", className: "nd-status-extra" },
  na: { label: "N/A", icon: "block", className: "nd-status-na" },
  not_applicable: { label: "N/A", icon: "block", className: "nd-status-na" },
  violation: { label: "VIOLATION", icon: "report", className: "nd-status-violation" },
  conflict: { label: "CONFLICT", icon: "warning", className: "nd-status-conflict" },
  undetermined: { label: "UNDETERMINED", icon: "help", className: "nd-status-undetermined" },
  neutral: { label: "NEUTRAL", icon: "circle", className: "nd-status-neutral" },
};

const KIND_LABELS = {
  document: "Document",
  cluster: "Cluster / Category",
  section: "Policy Section",
  topic: "Law Topic",
  law_chunk: "Law Clause",
};

function Field({ label, children }) {
  if (!children) return null;
  return (
    <div className="nd-field">
      <span className="nd-field-label">{label}</span>
      <span className="nd-field-value">{children}</span>
    </div>
  );
}

export default function NodeDetailPanel({ selected, analysis, onClose }) {
  if (!selected) return null;

  const status = STATUS_META[selected.status] || STATUS_META.neutral;
  const kindLabel = KIND_LABELS[selected.kind] || selected.kind;
  const extra = selected.extra || {};

  // Find matching obligation from analysis for law_chunk or topic nodes
  const obligation =
    analysis?.obligations?.find(
      (row) =>
        row.obligation_id === selected.id ||
        row.title === selected.title,
    ) || null;

  return (
    <div className="nd-panel" role="dialog" aria-label="Node details">
      {/* Header */}
      <div className="nd-header">
        <div className="nd-header-left">
          <span className={`nd-status-badge ${status.className}`}>
            <span className="material-symbols-outlined nd-status-icon">{status.icon}</span>
            {status.label}
          </span>
          <span className="nd-kind-label">{kindLabel}</span>
        </div>
        <button
          className="nd-close"
          type="button"
          onClick={onClose}
          aria-label="Close details"
          title="Close (Esc)"
        >
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>

      {/* Title */}
      <h3 className="nd-title">{selected.title || selected.id}</h3>

      {/* ID */}
      <div className="nd-id">
        <span className="material-symbols-outlined nd-id-icon">fingerprint</span>
        <code>{selected.id}</code>
      </div>

      {/* Body */}
      <div className="nd-body">
        {/* Summary / Description */}
        {selected.summary ? (
          <div className="nd-section">
            <h4 className="nd-section-title">
              <span className="material-symbols-outlined">description</span>
              Summary
            </h4>
            <p className="nd-summary-text">{selected.summary}</p>
          </div>
        ) : null}

        {/* Obligation details from analysis */}
        {obligation ? (
          <div className="nd-section">
            <h4 className="nd-section-title">
              <span className="material-symbols-outlined">gavel</span>
              Obligation Analysis
            </h4>
            {obligation.reason ? (
              <div className="nd-obligation-reason">
                <span className="nd-reason-label">Reasoning</span>
                <p>{obligation.reason}</p>
              </div>
            ) : null}
            {obligation.summary ? (
              <div className="nd-obligation-reason">
                <span className="nd-reason-label">Assessment</span>
                <p>{obligation.summary}</p>
              </div>
            ) : null}
            {obligation.severity ? (
              <Field label="Severity">{obligation.severity}</Field>
            ) : null}
            {obligation.evidence_quality ? (
              <Field label="Evidence Quality">
                {obligation.evidence_quality.replace(/_/g, " ")}
              </Field>
            ) : null}
            {obligation.matched_clauses?.length ? (
              <div className="nd-matched-clauses">
                <span className="nd-reason-label">
                  Matched Clauses ({obligation.matched_clauses.length})
                </span>
                {obligation.matched_clauses.slice(0, 3).map((clause, i) => (
                  <div className="nd-clause-card" key={clause.clause_id || i}>
                    <div className="nd-clause-header">
                      <code className="nd-clause-id">{clause.clause_id}</code>
                      {clause.section_title ? (
                        <span className="nd-clause-section">{clause.section_title}</span>
                      ) : null}
                    </div>
                    {clause.text ? (
                      <p className="nd-clause-text">
                        {clause.text.length > 240
                          ? clause.text.slice(0, 240) + "…"
                          : clause.text}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* Metadata fields */}
        <div className="nd-section">
          <h4 className="nd-section-title">
            <span className="material-symbols-outlined">info</span>
            Properties
          </h4>
          <div className="nd-fields-grid">
            <Field label="Node Type">{kindLabel}</Field>
            <Field label="Status">{status.label}</Field>
            {extra.act ? <Field label="Act">{extra.act.replace(/_/g, " ")}</Field> : null}
            {extra.chunk_type ? (
              <Field label="Chunk Type">{extra.chunk_type}</Field>
            ) : null}
            {extra.role ? <Field label="Role">{extra.role.replace(/_/g, " ")}</Field> : null}
            {extra.theme ? <Field label="Theme">{extra.theme.replace(/_/g, " ")}</Field> : null}
            {extra.topic_id ? (
              <Field label="Topic">{extra.topic_id.replace(/^TOPIC_/, "").replace(/_/g, " ")}</Field>
            ) : null}
            {extra.section_id ? (
              <Field label="Section ID"><code>{extra.section_id}</code></Field>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
