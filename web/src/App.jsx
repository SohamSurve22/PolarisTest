import { useEffect, useState } from "react";
import CoverageStrip from "./CoverageStrip.jsx";
import Findings, { policyNodeForClause } from "./Findings.jsx";
import GraphBoard from "./GraphBoard.jsx";
import Header from "./Header.jsx";
import LoadCard from "./LoadCard.jsx";
import PageHead from "./PageHead.jsx";
import { paintIdealFromAnalysis, paintPolicyFromAnalysis } from "./paintAnalysis.js";

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
  const [report, setReport] = useState(null);
  const [reportError, setReportError] = useState("");
  const [reportBusy, setReportBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [focusIdealId, setFocusIdealId] = useState(null);
  const [focusPolicyId, setFocusPolicyId] = useState(null);
  const [panToken, setPanToken] = useState(0);
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
    setFocusIdealId(null);
    setFocusPolicyId(null);
    setPanToken(0);
    setAnalysis(null);
    setAnalysisError("");
    setReport(null);
    setReportError("");
    setReportBusy(false);
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
        setBusy(false);
        setReportBusy(true);
        setReport(null);
        setReportError("");
        try {
          const reportResponse = await fetch("/api/report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(analyzePayload),
          });
          const reportPayload = await reportResponse.json();
          if (!reportResponse.ok) {
            const detail = reportPayload.detail;
            throw new Error(typeof detail === "string" ? detail : "Report failed");
          }
          setReport(reportPayload);
        } catch (reportErr) {
          setReportError(reportErr.message);
        } finally {
          setReportBusy(false);
        }
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
    setReport(null);
    setReportError("");
    setReportBusy(false);
    setSelected(null);
    setFocusIdealId(null);
    setFocusPolicyId(null);
    setPanToken(0);
    setLoadOpen(false);
  }

  const summary = counts(result);
  const paintedPolicy =
    result && analysis ? paintPolicyFromAnalysis(result.policy, analysis) : result?.policy;
  const paintedIdeal =
    result && analysis ? paintIdealFromAnalysis(result.ideal, analysis) : result?.ideal;
  const workspace = result != null;

  function selectFromPolicy(node) {
    setSelected(node);
    setFocusPolicyId(node.id);
    setFocusIdealId(null);
  }

  function selectFromIdeal(node) {
    setSelected(node);
    setFocusIdealId(node.id);
    setFocusPolicyId(null);
  }

  function selectFinding(row) {
    const lawNode = paintedIdeal?.nodes?.find((node) => node.id === row.obligation_id);
    setSelected(
      lawNode || {
        id: row.obligation_id,
        kind: "law_chunk",
        title: row.title,
        status: row.status === "partial" ? "weak" : row.status,
        summary: row.summary,
      },
    );
    setFocusIdealId(row.obligation_id);
    const clauseId = row.matched_clauses?.[0]?.clause_id || row.matched_clause_ids?.[0];
    setFocusPolicyId(policyNodeForClause(paintedPolicy, clauseId)?.id || null);
    setPanToken((value) => value + 1);
  }

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
          <CoverageStrip summary={summary} analysis={analysis} />
          <div className="workspace">
            <div className="graph-column">
              <GraphBoard
                title="User Graph (Generated)"
                hint="Green = section helped cover an obligation. Orange = partial. Red = only matched a gap."
                tone="user"
                graph={paintedPolicy}
                selectedId={focusPolicyId}
                panToken={panToken}
                onSelect={selectFromPolicy}
              />
              <GraphBoard
                title="Ideal Graph (Target)"
                hint="Green = covered obligation. Orange = partial. Red = missing. Matches the Analysis counts."
                tone="ideal"
                graph={paintedIdeal}
                selectedId={focusIdealId}
                panToken={panToken}
                onSelect={selectFromIdeal}
              />
            </div>
            <Findings
              analysis={analysis}
              analysisError={analysisError}
              busy={busy}
              selected={selected}
              onSelectFinding={selectFinding}
              report={report}
              reportError={reportError}
              reportBusy={reportBusy}
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
