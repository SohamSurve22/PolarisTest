import { useEffect, useMemo, useState } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";

const SIZE = {
  document: 128,
  cluster: 108,
  topic: 92,
  section: 92,
  law_chunk: 72,
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

function OrbitNode({ data }) {
  const sizeClass = data.hub ? " is-hub" : data.cluster ? " is-cluster" : data.chunk ? " is-chunk" : "";
  return (
    <div className={`orbit${sizeClass} orbit--${data.status || "neutral"}`}>
      <Handle type="target" position={Position.Top} id="t-top" />
      <Handle type="source" position={Position.Bottom} id="s-bottom" />
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
        >
          {data.collapsed ? "+" : "−"}
        </button>
      ) : null}
    </div>
  );
}

const nodeTypes = { orbit: OrbitNode };

function treeLayout(graph, collapsed, onToggle) {
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
  dag.setGraph({ rankdir: "TB", nodesep: 28, ranksep: 72, marginx: 24, marginy: 24 });
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
      position: { x: (placed?.x || 0) - size / 2, y: (placed?.y || 0) - size / 2 },
      data: {
        label: node.title || node.id,
        status: node.status,
        hub,
        cluster: node.kind === "cluster" && !hub,
        chunk: node.kind === "law_chunk",
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
    markerEnd: { type: MarkerType.ArrowClosed, width: 10, height: 7, color: "#424754" },
    style: { stroke: "#424754", strokeWidth: 1.2 },
  }));
  return { nodes, edges };
}

export default function GraphBoard({ title, hint, tone = "user", graph, onSelect }) {
  const [collapsed, setCollapsed] = useState(() => new Set());
  const graphKey = (graph?.nodes || []).map((node) => node.id).join("|");

  useEffect(() => {
    setCollapsed(new Set());
  }, [graphKey]);

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
    () => treeLayout(graph, collapsed, onToggle),
    [graph, collapsed],
  );
  const empty = !graph?.nodes?.length;
  return (
    <section className={`board tone-${tone}`}>
      <div className="board-overlay">
        <div className="board-badge" title={hint}>
          <span className="pulse-dot" />
          {title}
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
              minZoom={0.15}
              onNodeClick={(_, node) => onSelect(node.data.raw)}
              nodesConnectable={false}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="var(--grid)" gap={16} size={1} />
              <Controls position="top-right" showInteractive={false} />
            </ReactFlow>
          </ReactFlowProvider>
        )}
      </div>
    </section>
  );
}
