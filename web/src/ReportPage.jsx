import ReportPanel from "./ReportPanel.jsx";

export default function ReportPage({ report, reportError, onBack }) {
  return (
    <div className="report-page">
      <div className="report-page-bar">
        <button className="btn-secondary" type="button" onClick={onBack}>
          <span className="material-symbols-outlined">arrow_back</span>
          Back to Findings
        </button>
      </div>
      <ReportPanel report={report} reportError={reportError} busy={false} />
    </div>
  );
}
