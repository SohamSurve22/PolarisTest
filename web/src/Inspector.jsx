export default function Inspector({ selected, chunks, onClose }) {
  if (!selected) {
    return null;
  }
  return (
    <aside className="inspector-sheet" aria-label="Node inspector">
      <div className="inspector-head">
        <div>
          <span className="badge">{selected.kind}</span>
          <h3>{selected.title}</h3>
        </div>
        <button className="btn-ghost" type="button" onClick={onClose} aria-label="Close inspector">
          Close
        </button>
      </div>
      <p>{selected.summary || "No body text on this node."}</p>
      {chunks.map((chunk) => (
        <div className="law-item" key={chunk.id}>
          <strong>{chunk.title}</strong>
          <p>
            {chunk.extra?.act ? `${chunk.extra.act} · ` : ""}
            {chunk.summary}
          </p>
        </div>
      ))}
    </aside>
  );
}
