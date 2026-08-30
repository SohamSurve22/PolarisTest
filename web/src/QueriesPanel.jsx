import { useState } from "react";

const EXAMPLES = [
  {
    id: "withdraw",
    label: "Withdraw consent",
    question: "Can a Data Principal withdraw consent under the DPDP Act?",
  },
  {
    id: "43a",
    label: "IT Act 43A",
    question:
      "What is section 43A of the Information Technology Act about compensation for failure to protect data?",
  },
  {
    id: "certin",
    label: "CERT-In 6 hours",
    question: "How quickly must cyber incidents be reported to CERT-In?",
  },
];

function formatMs(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) {
    return "—";
  }
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)} s`;
  }
  return `${Math.round(n)} ms`;
}

function excerpt(text) {
  const body = (text || "").trim();
  if (body.length <= 280) {
    return body;
  }
  return `${body.slice(0, 280).trim()}…`;
}

export default function QueriesPanel() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("dense");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function onAsk(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setError("Enter a statute question.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/rag", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, mode }),
      });
      let payload = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }
      if (!response.ok) {
        if (response.status === 503) {
          throw new Error("Q&A backend unavailable (Qdrant or Ollama).");
        }
        const detail = payload.detail;
        throw new Error(typeof detail === "string" ? detail : "Question failed");
      }
      setResult(payload);
    } catch (err) {
      setResult(null);
      setError(err.message || "Question failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="queries-page">
      <form className="queries-card" onSubmit={onAsk}>
        <div className="form-group">
          <span className="queries-label">Retriever</span>
          <div className="queries-modes" role="group" aria-label="Retriever mode">
            <button
              type="button"
              className={`findings-filter${mode === "dense" ? " is-active" : ""}`}
              aria-pressed={mode === "dense"}
              disabled={busy}
              onClick={() => setMode("dense")}
            >
              Dense
            </button>
            <button
              type="button"
              className={`findings-filter${mode === "graph" ? " is-active" : ""}`}
              aria-pressed={mode === "graph"}
              disabled={busy}
              onClick={() => setMode("graph")}
            >
              Graph
            </button>
          </div>
        </div>
        <div className="form-group">
          <span className="queries-label">Examples</span>
          <div className="queries-examples">
            {EXAMPLES.map((item) => (
              <button
                key={item.id}
                type="button"
                className="findings-filter"
                disabled={busy}
                onClick={() => {
                  setQuestion(item.question);
                  setError("");
                }}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="queries-question">Statute question</label>
          <textarea
            id="queries-question"
            rows={4}
            value={question}
            disabled={busy}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask what the statute requires…"
          />
        </div>
        <div className="form-actions">
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? (
              <>
                <span className="spinner" /> Asking…
              </>
            ) : (
              <>
                <span className="material-symbols-outlined">search</span>
                Ask
              </>
            )}
          </button>
        </div>
        {error ? <div className="error-box">{error}</div> : null}
      </form>

      {result ? (
        <section className="queries-answer" aria-live="polite">
          <div className="queries-meta">
            <span className="meta-mono">Mode: {result.mode || mode}</span>
            <span className="meta-dot" />
            <span className="meta-mono">Retrieve {formatMs(result.retrieve_ms)}</span>
            <span className="meta-dot" />
            <span className="meta-mono">Generate {formatMs(result.generate_ms)}</span>
          </div>
          <p className="queries-answer-text">{result.answer}</p>
          {result.citations?.length ? (
            <ul className="queries-citations">
              {result.citations.map((row) => (
                <li key={row.id} className="queries-citation">
                  <div className="queries-citation-head">
                    <span className="meta-value">{row.id}</span>
                    {row.title ? <span className="queries-citation-title">{row.title}</span> : null}
                    <span className="meta-mono">
                      {Number.isFinite(Number(row.score)) ? Number(row.score).toFixed(3) : "—"}
                    </span>
                  </div>
                  {row.text ? (
                    <details>
                      <summary>Excerpt</summary>
                      <p>{excerpt(row.text)}</p>
                    </details>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
