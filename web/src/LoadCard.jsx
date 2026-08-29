export default function LoadCard({
  idPrefix,
  text,
  onText,
  file,
  onFile,
  busy,
  error,
  onCompare,
  onClear,
  compact,
}) {
  function onDrop(event) {
    event.preventDefault();
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) {
      onFile(dropped);
    }
  }

  return (
    <form
      className={`load-card${compact ? " is-compact" : ""}`}
      onSubmit={onCompare}
      onDragOver={(event) => event.preventDefault()}
      onDrop={onDrop}
    >
      <div className="drop-hint">
        Drop a privacy policy here, or paste text below
      </div>
      <div className="form-group">
        <label htmlFor={`${idPrefix}-text`}>Paste policy text</label>
        <textarea
          id={`${idPrefix}-text`}
          rows={compact ? 8 : 12}
          value={text}
          onChange={(event) => onText(event.target.value)}
          placeholder="Paste legal document text…"
        />
      </div>
      <div className="form-group">
        <label htmlFor={`${idPrefix}-file`}>Upload document</label>
        <input
          id={`${idPrefix}-file`}
          type="file"
          accept=".txt,.pdf,.docx,.html,.htm"
          onChange={(event) => onFile(event.target.files[0] || null)}
        />
        <div className="file-hint">
          {file ? file.name : "Supported: .txt .pdf .docx .html"}
        </div>
      </div>
      <div className="form-actions">
        <button className="btn-primary" type="submit" disabled={busy}>
          {busy ? (
            <>
              <span className="spinner" /> Comparing…
            </>
          ) : (
            "Compare"
          )}
        </button>
        <button className="btn-secondary" type="button" onClick={onClear}>
          Clear
        </button>
      </div>
      {error ? <div className="error-box">{error}</div> : null}
    </form>
  );
}
