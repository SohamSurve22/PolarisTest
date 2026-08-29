import { STATUS } from "./status.js";

export default function CoverageStrip({ summary }) {
  const ticks = [
    { key: "covered", value: summary.covered },
    { key: "weak", value: summary.weak },
    { key: "missing", value: summary.missing },
    { key: "extra", value: summary.extra },
  ];
  return (
    <div className="coverage-strip">
      <div className="coverage-counts">
        <span>
          <strong>{summary.sections}</strong> sections
        </span>
        <span>
          <strong>{summary.topics}</strong> topics
        </span>
        {ticks.map((tick) => (
          <span key={tick.key} className="coverage-tick">
            <span className="swatch" style={{ background: STATUS[tick.key].color }} />
            {STATUS[tick.key].label} {tick.value}
          </span>
        ))}
        <span className="coverage-tick">
          <span className="swatch" style={{ background: STATUS.mapped.color }} />
          {STATUS.mapped.label}
        </span>
      </div>
    </div>
  );
}
