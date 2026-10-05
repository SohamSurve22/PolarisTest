import { useEffect, useState } from "react";
import CoverageStrip from "./CoverageStrip.jsx";
import Findings, { policyNodeForClause } from "./Findings.jsx";
import GraphBoard from "./GraphBoard.jsx";
import Header from "./Header.jsx";
import LoadCard from "./LoadCard.jsx";

import PageHead from "./PageHead.jsx";
import QueriesPanel from "./QueriesPanel.jsx";
import ReportPage from "./ReportPage.jsx";
import LandingPage from "./LandingPage.jsx";
import { paintIdealFromAnalysis, paintPolicyFromAnalysis, paintPolicyFromJev } from "./paintAnalysis.js";

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
  const [userGraphMode, setUserGraphMode] = useState("path-a"); // "path-a" | "jev"
  const [loadOpen, setLoadOpen] = useState(false);
  const [view, setView] = useState(() => (
    ["#app", "#queries", "#report", "#validation"].includes(window.location.hash) ? "app" : "landing"
  ));
  const [tab, setTab] = useState(() => (window.location.hash === "#queries" ? "queries" : "validation"));
  const [reportPage, setReportPage] = useState(() => window.location.hash === "#report");

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

  useEffect(() => {
    function onHash() {
      const hash = window.location.hash;
      if (hash === "#queries") {
        setTab("queries");
        return;
      }
      setTab("validation");
      setReportPage(hash === "#report");
    }
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (tab === "queries") {
      if (window.location.hash !== "#queries") {
        window.location.hash = "queries";
      }
      return;
    }
    if (report && reportPage) {
      if (window.location.hash !== "#report") {
        window.location.hash = "report";
      }
      return;
    }
    if (!report && reportPage) {
      setReportPage(false);
    }
    if (window.location.hash === "#queries" || window.location.hash === "#report") {
      window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    }
  }, [report, reportPage, tab]);

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
    setReportPage(false);
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
    setReportPage(false);
    setSelected(null);
    setFocusIdealId(null);
    setFocusPolicyId(null);
    setPanToken(0);
    setLoadOpen(false);
  }

  const summary = counts(result);
  const paintedPolicy =
    result && analysis ? paintPolicyFromAnalysis(result.policy, analysis) : result?.policy;
  const jevPaintedPolicy =
    result && analysis ? paintPolicyFromJev(result.policy, analysis) : result?.policy;
  const paintedIdeal =
    result && analysis ? paintIdealFromAnalysis(result.ideal, analysis) : result?.ideal;
  const activeUserGraph = userGraphMode === "jev" ? jevPaintedPolicy : paintedPolicy;
  const hasJevData = !!(analysis?.obligations?.some((o) => o.jev_status));
  const workspace = result != null;
  const validationBusy = busy || reportBusy;

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

  function goTab(next) {
    setTab(next);
    if (next === "queries") {
      setLoadOpen(false);
    }
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

  const shellClass = [
    tab === "queries" ? "app is-queries" : workspace ? "app is-workspace" : "app is-landing",
    validationBusy ? "is-validating" : "",
  ]
    .filter(Boolean)
    .join(" ");

  if (view === "landing") {
    return (
      <LandingPage
        onExplore={() => {
          setView("app");
          setLoadOpen(true);
          window.location.hash = "app";
        }}
      />
    );
  }

  return (
    <div className={shellClass} aria-busy={validationBusy}>
      <Header
        theme={theme}
        tab={tab}
        onTab={goTab}
        onGoLanding={() => setView("landing")}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
      />
      {validationBusy ? (
        <div className="validation-overlay" role="status" aria-live="polite">
          <div className="validation-loader">
            <span className="validation-spinner" aria-hidden="true" />
            <span>{busy ? "Validating graph…" : "Finalizing validation…"}</span>
          </div>
        </div>
      ) : null}
      <PageHead
        tab={tab}
        fileName={file?.name}
        workspace={workspace}
        analysis={analysis}
        onLoadPolicy={() => {
          setError("");
          setLoadOpen(true);
        }}
      />

      {tab === "queries" ? (
        <QueriesPanel />
      ) : !workspace ? (
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
      ) : reportPage && report ? (
        <>
          <CoverageStrip summary={summary} analysis={analysis} />
          <div className="workspace">
            <ReportPage
              report={report}
              reportError={reportError}
              onBack={() => setReportPage(false)}
            />
          </div>
        </>
      ) : (
        <>
          <CoverageStrip summary={summary} analysis={analysis} />
          <div className="workspace">
            <div className="graph-column">
              <GraphBoard
                title="User Graph (Generated)"
                hint={
                  userGraphMode === "jev"
                    ? "Jev (Path B) — coloured by second-opinion AI status. Orange/red may differ from Path A."
                    : "Green = section helped cover an obligation. Orange = partial. Red = only matched a gap."
                }
                tone="user"
                graph={activeUserGraph}
                selectedId={focusPolicyId}
                panToken={panToken}
                onSelect={selectFromPolicy}
                selected={focusPolicyId ? selected : null}
                analysis={analysis}
                onClearSelection={() => {
                  setSelected(null);
                  setFocusIdealId(null);
                  setFocusPolicyId(null);
                }}
                graphMode={userGraphMode}
                onToggleGraphMode={() =>
                  setUserGraphMode((m) => (m === "path-a" ? "jev" : "path-a"))
                }
                hasJevData={hasJevData}
              />
              <GraphBoard
                title="Ideal Graph (Target)"
                hint="Green = covered obligation. Orange = partial. Red = missing. Matches the Analysis counts."
                tone="ideal"
                graph={paintedIdeal}
                selectedId={focusIdealId}
                panToken={panToken}
                onSelect={selectFromIdeal}
                selected={focusIdealId ? selected : null}
                analysis={analysis}
                onClearSelection={() => {
                  setSelected(null);
                  setFocusIdealId(null);
                  setFocusPolicyId(null);
                }}
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
              onViewReport={() => setReportPage(true)}
            />
          </div>
        </>
      )}

      {loadOpen && tab === "validation" ? (
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
