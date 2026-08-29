import { useEffect, useState } from "react";
import CoverageStrip from "./CoverageStrip.jsx";
import GraphBoard from "./GraphBoard.jsx";
import Header from "./Header.jsx";
import Inspector from "./Inspector.jsx";
import LoadCard from "./LoadCard.jsx";
import PageHead from "./PageHead.jsx";

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
    nodes: result?.policy?.nodes?.length || 0,
    edges: result?.policy?.edges?.length || 0,
  };
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem("polaris-theme") || "dark");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
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
    setAnalysis(null);
    setAnalysisError("");
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
      const analyzeBody = new FormData();
      analyzeBody.append("file", chosen);
      analyzeBody.append("jurisdiction", "IN");
      try {
        const analyzeResponse = await fetch("/api/analyze", { method: "POST", body: analyzeBody });
        const analyzePayload = await analyzeResponse.json();
        if (!analyzeResponse.ok) {
          const detail = analyzePayload.detail;
          throw new Error(typeof detail === "string" ? detail : "Analyze failed");
        }
        setAnalysis(analyzePayload);
      } catch (analyzeErr) {
        setAnalysisError(analyzeErr.message);
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
    setAnalysis(null);
    setAnalysisError("");
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
      />
      <PageHead
        fileName={file?.name}
        workspace={workspace}
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
        <>
          <CoverageStrip summary={summary} />
          <div className="workspace">
            <div className="graph-column">
              <GraphBoard
                title="User Graph (Generated)"
                hint="Clusters then nested sections. Use − / + on a node to collapse its branch."
                tone="user"
                graph={result.policy}
                onSelect={setSelected}
              />
              <GraphBoard
                title="Ideal Graph (Target)"
                hint="Statute → theme → topic → clause. Use − / + on a node to collapse its branch."
                tone="ideal"
                graph={result.ideal}
                onSelect={setSelected}
              />
            </div>
            <Inspector
              selected={selected}
              chunks={chunksForTopic}
              summary={summary}
              analysis={analysis}
              analysisError={analysisError}
              onClose={() => setSelected(null)}
            />
          </div>
        </>
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
              <h2 id="load-title">Run Validation</h2>
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
