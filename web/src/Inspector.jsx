const BADGE = {
  covered: { label: "MATCH", className: "badge-match" },
  mapped: { label: "MATCH", className: "badge-match" },
  weak: { label: "PARTIAL", className: "badge-partial" },
  missing: { label: "MISSING", className: "badge-missing" },
  extra: { label: "UNEXPECTED", className: "badge-extra" },
};

function pct(part, whole) {
  if (!whole) {
    return 0;
  }
  return Math.round((part / whole) * 100);
}

export default function Inspector({
  selected,
  chunks,
  summary,
  analysis,
  analysisError,
  onClose,
}) {
  const badge = selected ? BADGE[selected.status] : null;
  const obligationTotal = analysis?.obligations?.length || 0;
  const obligationCovered = analysis
    ? analysis.obligations.filter((row) => row.status === "covered").length
    : 0;
  const obligationPartial = analysis
    ? analysis.obligations.filter((row) => row.status === "partial").length
    : 0;
  const topicCoverage = pct(summary.covered, summary.topics);
  const sectionCoverage = pct(summary.sections - summary.extra, summary.sections);
  const hitRate = pct(summary.covered + summary.weak, summary.topics);
  const obligationCoverage = pct(obligationCovered, obligationTotal);
  const obligationPartialRate = pct(obligationPartial, obligationTotal);
  const obligationGapRate = pct(analysis?.gaps?.length || 0, obligationTotal);
  const conflict = selected && (selected.status === "weak" || selected.status === "missing");

  return (
    <aside className="inspector" aria-label="Comparison details">
      <div className="inspector-head">
        <div>
          <h2>Comparison Details</h2>
          <p>Select a node or edge to inspect</p>
        </div>
        {selected ? (
          <button className="btn-ghost" type="button" onClick={onClose} aria-label="Clear selection">
            Close
          </button>
        ) : null}
      </div>

      <div className="inspector-body">
        <AnalysisPanel analysis={analysis} analysisError={analysisError} />

        {selected ? (
          <div className="detail-card">
            <div className="detail-card-top">
              <span className="detail-kicker">NODE TYPE: {selected.kind?.toUpperCase()}</span>
              {badge ? <span className={`mono-badge ${badge.className}`}>{badge.label}</span> : null}
            </div>
            <div className="detail-title">{selected.title}</div>
            <div className="detail-id">ID: {selected.id}</div>
          </div>
        ) : (
          <div className="detail-card is-empty">
            <p>No node selected. Click a graph node to inspect type, match status, and linked clauses.</p>
          </div>
        )}

        {conflict ? (
          <section>
            <h3 className="inspector-section-title">
              <span className="material-symbols-outlined tone-conflict">warning</span>
              Active Conflict
            </h3>
            <div className="conflict-card">
              <div className="conflict-name">{selected.title}</div>
              <div className="value-grid">
                <div className="value-box">
                  <span className="value-kicker">USER GRAPH</span>
                  <span className="value-text">
                    {selected.status === "missing" ? "Not found" : "Partial coverage"}
                  </span>
                </div>
                <div className="value-box">
                  <span className="value-kicker">IDEAL GRAPH</span>
                  <span className="value-text">Required topic</span>
                </div>
              </div>
              <div className="reasoning-box">
                <span className="value-kicker">REASONING ENGINE</span>
                <p>
                  {selected.summary ||
                    "Keyword overlay found a weak or missing match for this ideal topic."}
                </p>
              </div>
            </div>
          </section>
        ) : null}

        {selected && !conflict && selected.summary ? (
          <section>
            <h3 className="inspector-section-title">Summary</h3>
            <p className="inspector-copy">{selected.summary}</p>
          </section>
        ) : null}

        <section>
          <h3 className="inspector-section-title">
            <span>Reference Trace</span>
            <span className="material-symbols-outlined tone-primary">timeline</span>
          </h3>
          {chunks.length ? (
            <ol className="trace">
              {chunks.map((chunk, index) => (
                <li
                  className={`trace-step${index === chunks.length - 1 ? " is-current" : ""}`}
                  key={chunk.id}
                >
                  <span className="trace-dot" />
                  <span className="trace-chip">
                    {chunk.extra?.act ? `${chunk.extra.act} · ` : ""}
                    {chunk.title}
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="inspector-copy muted">
              {selected?.kind === "topic"
                ? "No linked law chunks on this topic."
                : "Select an ideal topic to trace linked clauses."}
            </p>
          )}
        </section>

        {chunks.map((chunk) => (
          <div className="law-item" key={`law-${chunk.id}`}>
            <strong>{chunk.title}</strong>
            <p>
              {chunk.extra?.act ? `${chunk.extra.act} · ` : ""}
              {chunk.summary}
            </p>
          </div>
        ))}

        <section>
          <h3 className="inspector-section-title">
            {analysis ? "Obligation match" : "Keyword overlay"}
          </h3>
          <div className="fidelity">
            {analysis ? (
              <>
                <FidelityRow label="Covered" value={obligationCoverage} tone="primary" />
                <FidelityRow label="Partial" value={obligationPartialRate} tone="primary" />
                <FidelityRow
                  label="Gaps"
                  value={obligationGapRate}
                  tone={obligationGapRate > 20 ? "error" : "primary"}
                />
              </>
            ) : (
              <>
                <FidelityRow label="Topic coverage" value={topicCoverage} tone="primary" />
                <FidelityRow label="Section mapping" value={sectionCoverage} tone="primary" />
                <FidelityRow
                  label="Hit rate (incl. partial)"
                  value={hitRate}
                  tone={hitRate < 80 ? "error" : "primary"}
                />
              </>
            )}
          </div>
        </section>
      </div>
    </aside>
  );
}

function AnalysisPanel({ analysis, analysisError }) {
  if (analysisError && !analysis) {
    return (
      <section>
        <h3 className="inspector-section-title">Analysis</h3>
        <p className="inspector-copy muted">{analysisError}</p>
      </section>
    );
  }
  if (!analysis) {
    return (
      <section>
        <h3 className="inspector-section-title">Analysis</h3>
        <p className="inspector-copy muted">Run validation to score obligations against Indian website-privacy law.</p>
      </section>
    );
  }
  const covered = analysis.obligations.filter((row) => row.status === "covered").length;
  const violation = analysis.obligations.filter((row) => row.status === "violation").length;
  const conflict = analysis.obligations.filter((row) => row.status === "conflict").length;
  const applicable = analysis.obligations.filter((row) => row.status !== "not_applicable").length;
  const mix =
    violation + conflict > 0
      ? `${violation} violation · ${conflict} conflict · ${covered}/${applicable} applicable covered`
      : `${covered}/${applicable} applicable covered · ${analysis.gaps.length} gaps`;
  return (
    <section>
      <h3 className="inspector-section-title">Analysis</h3>
      <p className="inspector-copy">
        {analysis.jurisdiction}
        {analysis.applicable_laws?.length ? ` · ${analysis.applicable_laws.join(", ")}` : ""}
      </p>
      <p className="inspector-copy muted">{mix}</p>
      {analysis.gaps?.length ? (
        <ul className="analysis-list">
          {analysis.gaps.map((gap) => (
            <li key={gap.obligation_id}>
              <span
                className={`mono-badge badge-${
                  gap.status === "partial"
                    ? "partial"
                    : gap.status === "violation"
                      ? "violation"
                      : gap.status === "conflict"
                        ? "conflict"
                        : "missing"
                }`}
              >
                {gap.status.toUpperCase()}
              </span>{" "}
              {gap.act ? `${gap.act} · ` : ""}
              {gap.title}
            </li>
          ))}
        </ul>
      ) : (
        <p className="inspector-copy muted">No obligation gaps.</p>
      )}
      {analysis.penalties?.length ? (
        <>
          <h3 className="inspector-section-title">Penalties</h3>
          <ul className="analysis-list">
            {analysis.penalties.map((pen) => (
              <li key={`${pen.obligation_id}-${pen.title}`}>
                {pen.title}
                {pen.amount_crore != null ? ` · ₹${pen.amount_crore} crore` : ""}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function FidelityRow({ label, value, tone }) {
  return (
    <div>
      <div className="fidelity-row">
        <span>{label}</span>
        <span className={tone === "error" ? "tone-error" : ""}>{value}%</span>
      </div>
      <div className="fidelity-track">
        <div
          className={`fidelity-fill tone-${tone}`}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
    </div>
  );
}
