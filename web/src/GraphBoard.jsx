import { useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";

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

export default function GraphBoard({ title, hint, graph, mode, onSelect }) {
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
              <Background color="var(--grid)" gap={22} />
              <Controls showInteractive={false} />
            </ReactFlow>
          </ReactFlowProvider>
        )}
      </div>
    </section>
  );
}
