"""OpenIE GraphIR → ViewGraph projection (Path C).

Reuses the existing PolicyGraphBuilder + normalize stack; nothing in this
module learns new ontology. GraphIR stays the machine output
(AnalysisResult.policy_graph), and this module only projects to the
ViewGraph that the UI renders.
"""

from __future__ import annotations

from typing import Any

from policy_compare.models import ViewEdge, ViewGraph, ViewNode
from policy_compare.policy_view import policy_view_graph

# Small set of ViewGraph kinds for the OpenIE canvas. Unknown GraphIR labels
# still render as "entity" rather than inventing new ones.
_OPENIE_NODE_KINDS: dict[str, str] = {
    "Actor": "entity",
    "Entity": "entity",
    "PrivacyPractice": "practice",
    "SecurityPractice": "practice",
    "Consent": "practice",
    "RetentionPolicy": "practice",
}
_OPENIE_EDGE_KINDS: frozenset[str] = frozenset(
    {
        "COLLECTS",
        "SHARES",
        "RETAINS",
        "RETURNS",
        "USES",
        "PROCESSES",
        "HAS_OBLIGATION",
        "REFERENCES",
        "DERIVED_FROM",
    }
)


def graph_ir_to_view_graph(graph_ir: dict[str, Any], document_id: str) -> ViewGraph:
    """Project a GraphIR dictionary onto a document-hub ViewGraph."""
    doc_id = document_id or ""
    doc_hub = f"doc:{doc_id}"
    doc_title = _doc_title(graph_ir)

    nodes: list[ViewNode] = [ViewNode(id=doc_hub, kind="document", title=doc_title)]
    edges: list[ViewEdge] = []

    node_ids: set[str] = set()
    for raw_node in graph_ir.get("nodes", []):
        node_id = raw_node.get("id", "")
        node_ids.add(node_id)
        kind = _node_kind(raw_node.get("label"))
        nodes.append(
            ViewNode(
                id=node_id,
                kind=kind,
                title=str(raw_node.get("properties", {}).get("name", "") or node_id),
                extra={
                    "source_clause": raw_node.get("source_clause"),
                    "clause_id": raw_node.get("properties", {}).get("clause_id"),
                    "evidence": raw_node.get("properties", {}).get("evidence", ""),
                    "mapping_failures": 0,
                },
            )
        )

    mapping_failures_by_node: dict[str, int] = {}
    for raw_failure in graph_ir.get("mapping_failures", []):
        source = raw_failure.get("source_clause") or raw_failure.get("subject", "")
        if source:
            mapping_failures_by_node[source] = mapping_failures_by_node.get(source, 0) + 1

    for node_id, count in mapping_failures_by_node.items():
        for node in nodes:
            if node.id == node_id:
                node.extra["mapping_failures"] = count

    for raw_rel in graph_ir.get("relationships", []):
        rel_type = raw_rel.get("type", "")
        if rel_type not in _OPENIE_EDGE_KINDS:
            continue
        source = raw_rel.get("source", "")
        target = raw_rel.get("target", "")
        if source in node_ids and target in node_ids:
            edges.append(
                ViewEdge(
                    source=source,
                    target=target,
                    type=rel_type,
                )
            )

    return ViewGraph(nodes=nodes, edges=edges)


def _node_kind(label: str | None) -> str:
    if not label:
        return "entity"
    return _OPENIE_NODE_KINDS.get(label, "entity")


def _doc_title(graph_ir: dict[str, Any]) -> str:
    metadata = graph_ir.get("metadata") or {}
    title = metadata.get("title") or metadata.get("filename") or "OpenIE policy"
    return str(title)
