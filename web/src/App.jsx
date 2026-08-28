import { useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";

const STATUS = {
  covered: { color: "var(--covered)", label: "Covered" },
  weak: { color: "var(--weak)", label: "Partial" },
  missing: { color: "var(--missing)", label: "Missing" },
  mapped: { color: "var(--mapped)", label: "In policy" },
  extra: { color: "var(--extra)", label: "Extra" },
};

function OrbitNode({ data }) {
  return (
    <div className={`orbit${data.hub ? " is-hub" : ""} orbit--${data.status || "neutral"}`}>
      <Handle type="target" position={Position.Top} id="t-top" />
      <Handle type="target" position={Position.Right} id="t-right" />
      <Handle type="target" position={Position.Bottom} id="t-bottom" />
      <Handle type="target" position={Position.Left} id="t-left" />
      <Handle type="source" position={Position.Top} id="s-top" />
      <Handle type="source" position={Position.Right} id="s-right" />
      <Handle type="source" position={Position.Bottom} id="s-bottom" />
      <Handle type="source" position={Position.Left} id="s-left" />
      <span className="orbit-label">{data.label}</span>
    </div>
  );
}

const nodeTypes = { orbit: OrbitNode };

function spokeHandle(index, total) {
  const angle = -Math.PI / 2 + (2 * Math.PI * index) / Math.max(total, 1);
  const deg = ((angle * 180) / Math.PI + 360) % 360;
  if (deg >= 315 || deg < 45) return { source: "s-right", target: "t-left" };
  if (deg < 135) return { source: "s-bottom", target: "t-top" };
  if (deg < 225) return { source: "s-left", target: "t-right" };
  return { source: "s-top", target: "t-bottom" };
}

function starLayout(hub, spokes) {
  const hubSize = 128;
  const spokeSize = 92;
  const cx = 420;
  const cy = 340;
  const radius = Math.max(230, 90 + spokes.length * 9);
  const placed = [];
  if (hub) {
    placed.push({
      id: hub.id,
      type: "orbit",
      position: { x: cx - hubSize / 2, y: cy - hubSize / 2 },
      data: { label: hub.title || hub.id, status: hub.status, hub: true, raw: hub },
    });
  }
  spokes.forEach((spoke, index) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / Math.max(spokes.length, 1);
    placed.push({
      id: spoke.id,
      type: "orbit",
      position: {
        x: cx + radius * Math.cos(angle) - spokeSize / 2,
        y: cy + radius * Math.sin(angle) - spokeSize / 2,
      },
      data: { label: spoke.title || spoke.id, status: spoke.status, hub: false, raw: spoke },
    });
  });
  const edges = spokes.map((spoke, index) => {
    const handles = spokeHandle(index, spokes.length);
    return {
      id: `${hub.id}-${spoke.id}`,
      source: hub.id,
      target: spoke.id,
      sourceHandle: handles.source,
      targetHandle: handles.target,
      markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: "#8b949e" },
      style: { stroke: "#8b949e", strokeWidth: 1.4 },
    };
  });
  return { nodes: placed, edges };
}

function layoutPolicy(graph) {
  const nodes = graph?.nodes || [];
  const hub = nodes.find((node) => node.kind === "document") || nodes[0];
  const spokes = nodes.filter((node) => node.kind === "section");
  if (!hub) return { nodes: [], edges: [] };
  return starLayout(hub, spokes);
}

function layoutIdeal(graph) {
  const topics = (graph?.nodes || []).filter((node) => node.kind === "topic");
  const hub = {
    id: "__ideal_hub",
    kind: "hub",
    title: "Ideal policy",
    summary: "Topics a private-company website privacy policy should cover.",
    status: "neutral",
  };
  return starLayout(hub, topics);
}

function GraphBoard({ title, hint, graph, mode, onSelect }) {
  const { nodes, edges } = useMemo(
    () => (mode === "ideal" ? layoutIdeal(graph) : layoutPolicy(graph)),
    [graph, mode],
  );
  const empty = !graph?.nodes?.length;
  return (
    <section className="board">
      <div className="board-head">
        <h2>{title}</h2>
        <p>{hint}</p>
      </div>
      <div className="flow">
        {empty ? (
          <div className="empty-state">No graph yet.</div>
        ) : (
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.25}
              onNodeClick={(_, node) => onSelect(node.data.raw)}
              nodesConnectable={false}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#30363d" gap={22} />
              <Controls showInteractive={false} />
            </ReactFlow>
          </ReactFlowProvider>
        )}
      </div>
    </section>
  );
}

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

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("polaris-theme", theme);
  }, [theme]);

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
      if (!file) {
        setFile(chosen);
      }
    } catch (err) {
      setError(err.message);
      setResult(null);
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

  return (
    <div className="app">
      <header>
        <div>
          <h1>PolarisLex Policy Overlay</h1>
          <span className="subtitle">
            Compare a private-company website privacy policy against the ideal topic graph
          </span>
        </div>
        <button
          className="theme-toggle"
          type="button"
          role="switch"
          aria-checked={theme === "light"}
          aria-label="Toggle light mode"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          Dark
          <span className="switch" />
          Light
        </button>
      </header>

      <div className="pane-container">
        <div className="pane">
          <h2>Input</h2>
          <form onSubmit={compare}>
            <div className="form-group">
              <label htmlFor="text">Paste policy text</label>
              <textarea
                id="text"
                rows={18}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Paste legal document text here, or upload a file below..."
              />
            </div>
            <div className="form-group">
              <label htmlFor="file">Upload document</label>
              <input
                id="file"
                type="file"
                accept=".txt,.pdf,.docx,.html,.htm"
                onChange={(event) => setFile(event.target.files[0] || null)}
              />
              <div className="file-hint">Supported: .txt .pdf .docx .html</div>
            </div>
            <div className="form-actions">
              <button className="btn-primary" type="submit" disabled={busy}>
                {busy ? <><span id="spinner" /> Comparing...</> : "Compare Policy"}
              </button>
              <button className="btn-secondary" type="button" onClick={clearAll}>
                Clear
              </button>
            </div>
          </form>
          {error ? <div className="error-box">{error}</div> : null}
        </div>

        <div className="pane">
          <h2>Output</h2>
          {!result ? (
            <div className="empty-state">
              <p>
                Paste text or upload a document, then click <strong>Compare Policy</strong>.
              </p>
            </div>
          ) : (
            <>
              <h3>Coverage</h3>
              <table className="metadata-table">
                <tbody>
                  <tr><td>File</td><td>{file?.name || "pasted.txt"}</td></tr>
                  <tr><td>Policy sections</td><td>{summary.sections}</td></tr>
                  <tr><td>Ideal topics</td><td>{summary.topics}</td></tr>
                  <tr><td>Covered</td><td>{summary.covered}</td></tr>
                  <tr><td>Partial</td><td>{summary.weak}</td></tr>
                  <tr><td>Missing</td><td>{summary.missing}</td></tr>
                  <tr><td>Extra sections</td><td>{summary.extra}</td></tr>
                </tbody>
              </table>
              <h3>
                Inspector
                {selected ? <span className="badge">{selected.kind}</span> : null}
              </h3>
              <div className="inspector">
                {selected ? (
                  <>
                    <h4>{selected.title}</h4>
                    <p>{selected.summary || "No body text on this node."}</p>
                    {chunksForTopic.map((chunk) => (
                      <div className="law-item" key={chunk.id}>
                        <strong>{chunk.title}</strong>
                        <p>
                          {chunk.extra?.act ? `${chunk.extra.act} · ` : ""}
                          {chunk.summary}
                        </p>
                      </div>
                    ))}
                  </>
                ) : (
                  <p>Click a center hub or a ring node in the graphs below.</p>
                )}
              </div>
              <div className="legend">
                {Object.entries(STATUS).map(([key, value]) => (
                  <span key={key}>
                    <span className="swatch" style={{ background: value.color }} />
                    {value.label}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {result ? (
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
      ) : null}
    </div>
  );
}
