export default function PageHead({ fileName, workspace, onLoadPolicy }) {
  return (
    <div className="page-head">
      <div>
        <h1 className="page-title">Graph Validation</h1>
        <p className="page-meta">
          {workspace ? (
            <>
              <span className="page-meta-item">
                <span className="material-symbols-outlined meta-icon">policy</span>
                Policy: <span className="meta-value">{fileName || "pasted.txt"}</span>
              </span>
              <span className="meta-dot" />
              <span className="meta-mono">Version: overlay</span>
            </>
          ) : (
            <span className="page-meta-item">Load a policy to overlay against the ideal graph</span>
          )}
        </p>
      </div>
      {workspace ? (
        <div className="page-actions">
          <button className="btn-primary" type="button" onClick={onLoadPolicy}>
            <span className="material-symbols-outlined">play_arrow</span>
            Run Validation
          </button>
        </div>
      ) : null}
    </div>
  );
}
