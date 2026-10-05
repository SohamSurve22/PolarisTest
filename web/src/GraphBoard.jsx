import { useEffect, useMemo, useState } from "react";
import dagre from "@dagrejs/dagre";
import NodeDetailPanel from "./NodeDetailPanel.jsx";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";

const SIZE = {
  document: 128,
  cluster: 108,
  topic: 92,
  section: 92,
  law_chunk: 72,
  entity: 72,
  data: 64,
  practice: 64,
};

function sizeFor(kind) {
  return SIZE[kind] || 92;
}

function childMap(edges) {
  const map = new Map();
  for (const edge of edges) {
    if (!map.has(edge.source)) {
      map.set(edge.source, []);
    }
    map.get(edge.source).push(edge.target);
  }
  return map;
}

function parentMap(edges) {
  const map = new Map();
  for (const edge of edges) {
    map.set(edge.target, edge.source);
  }
  return map;
}

function hiddenIds(collapsed, edges) {
  const children = childMap(edges);
  const hidden = new Set();
  function walk(id) {
    for (const child of children.get(id) || []) {
      hidden.add(child);
      walk(child);
    }
  }
  collapsed.forEach(walk);
  return hidden;
}

function ancestorsOf(id, edges) {
  const parents = parentMap(edges);
  const chain = [];
  let current = id;
  while (parents.has(current)) {
    current = parents.get(current);
    chain.push(current);
  }
  return chain;
}

function OrbitNode({ data }) {
  const sizeClass = data.hub ? " is-hub" : data.cluster ? " is-cluster" : data.chunk ? " is-chunk" : "";
  const selectedClass = data.selected ? " is-selected" : "";
  const status = data.status || "neutral";
  return (
    <div
      className={`orbit${sizeClass}${selectedClass} orbit--${status}`}
      title={data.label}
    >
      <Handle type="target" position={Position.Top} id="t-top" className="orbit-handle" />
      <Handle type="source" position={Position.Bottom} id="s-bottom" className="orbit-handle" />

      {data.hub ? (
        <span className="orbit-kicker">ROOT</span>
      ) : data.cluster ? (
        <span className="orbit-kicker">GROUP</span>
      ) : null}

      <span className="orbit-label">{data.label}</span>

      {data.hasChildren ? (
        <button
          className="orbit-toggle nodrag nopan"
          type="button"
          aria-expanded={!data.collapsed}
          aria-label={data.collapsed ? "Expand children" : "Collapse children"}
          onClick={(event) => {
            event.stopPropagation();
            data.onToggle();
          }}
          title={data.collapsed ? "Expand children" : "Collapse children"}
        >
          {data.collapsed ? "+" : "−"}
        </button>
      ) : null}
    </div>
  );
}

const nodeTypes = { orbit: OrbitNode };

function FitSelected({ selectedId, panToken }) {
  const { fitView, getNode } = useReactFlow();
  useEffect(() => {
    if (!selectedId || !panToken) {
      return undefined;
    }
    let attempts = 0;
    let timer = 0;
    function tryFit() {
      const node = getNode(selectedId);
      if (node) {
        fitView({ nodes: [node], padding: 0.75, duration: 280 });
        return;
      }
      if (attempts < 8) {
        attempts += 1;
        timer = window.setTimeout(tryFit, 40);
      }
    }
    tryFit();
    return () => window.clearTimeout(timer);
  }, [selectedId, panToken, fitView, getNode]);
  return null;
}

function FitOnFullscreen({ isFullscreen }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    const timer = window.setTimeout(() => {
      fitView({ padding: 0.18, duration: 250 });
    }, 80);
    return () => window.clearTimeout(timer);
  }, [isFullscreen, fitView]);
  return null;
}

function treeLayout(graph, collapsed, onToggle, selectedId) {
  const rawNodes = graph?.nodes || [];
  const rawEdges = graph?.edges || [];
  if (!rawNodes.length) {
    return { nodes: [], edges: [] };
  }
  const hidden = hiddenIds(collapsed, rawEdges);
  const visible = rawNodes.filter((node) => !hidden.has(node.id));
  const visibleIds = new Set(visible.map((node) => node.id));
  const visibleEdges = rawEdges.filter(
    (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
  );
  const children = childMap(rawEdges);

  const dag = new dagre.graphlib.Graph();
  dag.setGraph({ rankdir: "TB", nodesep: 36, ranksep: 84, marginx: 32, marginy: 32 });
  dag.setDefaultEdgeLabel(() => ({}));
  visible.forEach((node) => {
    const size = sizeFor(node.kind);
    dag.setNode(node.id, { width: size, height: size });
  });
  visibleEdges.forEach((edge) => {
    dag.setEdge(edge.source, edge.target);
  });
  dagre.layout(dag);

  const nodes = visible.map((node) => {
    const placed = dag.node(node.id);
    const size = sizeFor(node.kind);
  const hub = node.kind === "document" || node.extra?.role === "ideal_hub";
  const kids = children.get(node.id) || [];
  return {
    id: node.id,
    type: "orbit",
    selected: node.id === selectedId,
    position: { x: (placed?.x || 0) - size / 2, y: (placed?.y || 0) - size / 2 },
    data: {
      label: node.title || node.id,
      status: node.status,
      hub,
      cluster: node.kind === "cluster" && !hub,
      chunk: node.kind === "law_chunk",
      entity: node.kind === "entity",
      data: node.kind === "data",
      practice: node.kind === "practice",
      raw: node,
      hasChildren: kids.length > 0,
      collapsed: collapsed.has(node.id),
      onToggle: () => onToggle(node.id),
    },
  };
  });
  const edges = visibleEdges.map((edge) => ({
    id: `${edge.source}-${edge.target}-${edge.type}`,
    source: edge.source,
    target: edge.target,
    sourceHandle: "s-bottom",
    targetHandle: "t-top",
    type: "smoothstep",
    animated: edge.type === "governs" || edge.status === "active",
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 9,
      height: 7,
      color: "color-mix(in srgb, var(--border) 80%, white)",
    },
    style: {
      stroke: "color-mix(in srgb, var(--border) 75%, transparent)",
      strokeWidth: 1.5,
    },
  }));
  return { nodes, edges };
}

export default function GraphBoard({
  title,
  hint,
  tone = "user",
  graph,
  selectedId,
  panToken = 0,
  onSelect,
  selected,
  analysis,
  onClearSelection,
  graphMode,
  onToggleGraphMode,
  hasJevData,
}) {
  const [collapsed, setCollapsed] = useState(() => new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);
  const graphKey = (graph?.nodes || []).map((node) => node.id).join("|");

  useEffect(() => {
    setCollapsed(new Set());
  }, [graphKey]);

  useEffect(() => {
    if (!isFullscreen) return;
    function onKeyDown(e) {
      if (e.key === "Escape") {
        setIsFullscreen(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullscreen]);

  useEffect(() => {
    if (!selectedId || !graph?.edges?.length) {
      return;
    }
    const toOpen = ancestorsOf(selectedId, graph.edges);
    if (!toOpen.length) {
      return;
    }
    setCollapsed((current) => {
      if (toOpen.every((id) => !current.has(id))) {
        return current;
      }
      const next = new Set(current);
      toOpen.forEach((id) => next.delete(id));
      return next;
    });
  }, [selectedId, graphKey]);

  function onToggle(id) {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  const { nodes, edges } = useMemo(
    () => treeLayout(graph, collapsed, onToggle, selectedId),
    [graph, collapsed, selectedId],
  );
  const empty = !graph?.nodes?.length;
  return (
    <section className={`board tone-${tone}${isFullscreen ? " is-fullscreen" : ""}`}>
      <div className="board-overlay">
        <div className="board-header-left">
          <div className="board-badge" title={hint}>
            <span className="pulse-dot" />
            {title}
            {isFullscreen ? <span className="fullscreen-badge">FULLSCREEN</span> : null}
          </div>
          {onToggleGraphMode ? (
            <div className="graph-mode-toggle" role="group" aria-label="Graph view mode">
              <button
                id="graph-mode-path-a"
                className={`graph-mode-btn${!graphMode || graphMode === "path-a" ? " is-active" : ""}`}
                type="button"
                onClick={() => graphMode !== "path-a" && onToggleGraphMode()}
                aria-pressed={!graphMode || graphMode === "path-a"}
                title="Path A — standard compliance analysis"
              >
                Path A
              </button>
              <button
                id="graph-mode-jev"
                className={`graph-mode-btn${graphMode === "jev" ? " is-active" : ""}${!hasJevData ? " is-dim" : ""}`}
                type="button"
                onClick={() => graphMode !== "jev" && onToggleGraphMode()}
                aria-pressed={graphMode === "jev"}
                title={hasJevData ? "Jev — second-opinion AI view" : "Jev data not yet available"}
              >
                Jev
                {!hasJevData && <span className="graph-mode-badge">–</span>}
              </button>
            </div>
          ) : null}
          {isFullscreen ? (
            <button
              className="btn-exit-fullscreen"
              type="button"
              onClick={() => setIsFullscreen(false)}
              title="Exit Full Screen (Esc)"
            >
              <span className="material-symbols-outlined">fullscreen_exit</span>
              Exit Full Screen
            </button>
          ) : null}
        </div>
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
              fitViewOptions={{ padding: 0.18 }}
              minZoom={0.08}
              maxZoom={3}
              zoomOnScroll={true}
              preventScrolling={true}
              panOnScroll={false}
              onNodeClick={(_, node) => onSelect(node.data.raw)}
              nodesConnectable={false}
              proOptions={{ hideAttribution: true }}
            >
              <FitSelected selectedId={selectedId} panToken={panToken} />
              <FitOnFullscreen isFullscreen={isFullscreen} />
              <Background
                variant="dots"
                gap={22}
                size={1.2}
                color="color-mix(in srgb, var(--border) 40%, transparent)"
              />
              <Controls
                position="top-right"
                showInteractive={false}
                onFitView={() => setIsFullscreen((prev) => !prev)}
              />
            </ReactFlow>
          </ReactFlowProvider>
        )}
        {selected ? (
          <NodeDetailPanel
            selected={selected}
            analysis={analysis}
            onClose={onClearSelection}
          />
        ) : null}
      </div>
    </section>
  );
}
