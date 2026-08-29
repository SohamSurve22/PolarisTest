import { useEffect, useState } from "react";
import CoverageStrip from "./CoverageStrip.jsx";
import GraphBoard from "./GraphBoard.jsx";
import Header from "./Header.jsx";
import Inspector from "./Inspector.jsx";
import LoadCard from "./LoadCard.jsx";

function counts(result) {
  const topics = result?.ideal?.nodes?.filter((node) => node.kind === "topic") || [];
  return {
    covered: topics.filter((node) => node.status === "covered").length,
    weak: topics.filter((node) => node.status === "weak").length,
    missing: topics.filter((node) => node.status === "missing").length,
    extra:
      result?.policy?.nodes?.filter(
        (node) => node.kind === "section" && node.status === "extra",
      ).length || 0,
    sections: result?.policy?.nodes?.filter((node) => node.kind === "section").length || 0,
    topics: topics.length,
  };
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem("polaris-theme") || "dark");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(null);
  const [loadOpen, setLoadOpen] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("polaris-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!loadOpen) {
      return undefined;
    }
    function onKey(event) {
      if (event.key === "Escape" && !busy) {
        setLoadOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [loadOpen, busy]);

  async function compare(event) {
    event?.preventDefault();
    let chosen = file;
    if (!chosen && text.trim()) {
      chosen = new File([text], "pasted.txt", { type: "text/plain" });
    }
    if (!chosen) {
      setError("Paste text or upload a file.");
      return;
    }
    setBusy(true);
    setError("");
    setSelected(null);
    const body = new FormData();
    body.append("file", chosen);
    try {
      const response = await fetch("/api/compare", { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) {
        const detail = payload.detail;
        throw new Error(typeof detail === "string" ? detail : "Compare failed");
      }
      setResult(payload);
      setLoadOpen(false);
      if (!file) {
        setFile(chosen);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function clearAll() {
    setText("");
    setFile(null);
    setError("");
    setResult(null);
    setSelected(null);
    setLoadOpen(false);
  }

  const summary = counts(result);
  const chunksForTopic =
    selected?.kind === "topic" && result
      ? result.ideal.nodes.filter(
          (node) =>
            node.kind === "law_chunk" &&
            result.ideal.edges.some(
              (edge) => edge.source === selected.id && edge.target === node.id,
            ),
        )
      : [];
  const workspace = result != null;

  return (
    <div className={`app${workspace ? " is-workspace" : " is-landing"}`}>
      <Header
        theme={theme}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
        workspace={workspace}
        fileName={file?.name}
        onLoadPolicy={() => {
          setError("");
          setLoadOpen(true);
        }}
      />

      {!workspace ? (
        <main className="landing">
          <LoadCard
            idPrefix="landing"
            text={text}
            onText={setText}
            file={file}
            onFile={setFile}
            busy={busy}
            error={error}
            onCompare={compare}
            onClear={clearAll}
          />
        </main>
      ) : (
        <main className="workspace">
          <CoverageStrip summary={summary} />
          <div className="graph-row">
            <GraphBoard
              title="This policy"
              hint="Document at the center, sections on the ring"
              graph={result.policy}
              mode="policy"
              onSelect={setSelected}
            />
            <GraphBoard
              title="Ideal coverage"
              hint="Ideal hub at the center, law topics on the ring"
              graph={result.ideal}
              mode="ideal"
              onSelect={setSelected}
            />
          </div>
          <Inspector selected={selected} chunks={chunksForTopic} onClose={() => setSelected(null)} />
        </main>
      )}

      {loadOpen ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={() => {
            if (!busy) {
              setLoadOpen(false);
            }
          }}
        >
          <div
            className="modal"
            role="dialog"
            aria-labelledby="load-title"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-head">
              <h2 id="load-title">Load policy</h2>
              <button
                className="btn-ghost"
                type="button"
                disabled={busy}
                onClick={() => setLoadOpen(false)}
              >
                Close
              </button>
            </div>
            <LoadCard
              idPrefix="modal"
              compact
              text={text}
              onText={setText}
              file={file}
              onFile={setFile}
              busy={busy}
              error={error}
              onCompare={compare}
              onClear={clearAll}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
