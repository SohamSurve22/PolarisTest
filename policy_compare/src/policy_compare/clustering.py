"""Attach topic-cluster and Extra nodes onto a matched policy graph."""

from __future__ import annotations

from policy_compare.models import MatchLink, ViewEdge, ViewGraph, ViewNode
from policy_compare.topics import base_topic_id, topic_title

_EXTRA_ID = "cluster:extra"


def cluster_policy_graph(policy: ViewGraph, links: list[MatchLink]) -> ViewGraph:
  """Document → topic clusters → top-level sections; nested CONTAINS under parents."""
  document = next(node for node in policy.nodes if node.kind == "document")
  sections = [node for node in policy.nodes if node.kind == "section"]
  section_ids = {node.id for node in sections}

  best: dict[str, MatchLink] = {}
  for link in links:
    current = best.get(link.policy_section_id)
    if current is None or link.score > current.score:
      best[link.policy_section_id] = link

  def _is_top(section: ViewNode) -> bool:
    parent = (section.extra or {}).get("parent_section_id") or ""
    if not parent:
      return True
    return f"section:{parent}" not in section_ids

  cluster_nodes: dict[str, ViewNode] = {}
  edges: list[ViewEdge] = []
  extra_needed = False

  for section in sections:
    if _is_top(section):
      link = best.get(section.id)
      if link is None or section.status == "extra":
        extra_needed = True
        edges.append(ViewEdge(source=_EXTRA_ID, target=section.id, type="CONTAINS"))
        continue
      base = base_topic_id(link.topic_id)
      cluster_id = f"cluster:policy:{base}"
      if cluster_id not in cluster_nodes:
        cluster_nodes[cluster_id] = ViewNode(
          id=cluster_id,
          kind="cluster",
          title=topic_title(base),
          extra={"role": "topic_cluster", "topic_id": base},
        )
      edges.append(ViewEdge(source=cluster_id, target=section.id, type="CONTAINS"))
    else:
      parent = section.extra.get("parent_section_id") or ""
      edges.append(
        ViewEdge(source=f"section:{parent}", target=section.id, type="CONTAINS"),
      )

  for cluster_id in cluster_nodes:
    edges.append(ViewEdge(source=document.id, target=cluster_id, type="CONTAINS"))
  if extra_needed:
    cluster_nodes[_EXTRA_ID] = ViewNode(
      id=_EXTRA_ID,
      kind="cluster",
      title="Extra",
      extra={"role": "extra"},
    )
    edges.append(ViewEdge(source=document.id, target=_EXTRA_ID, type="CONTAINS"))

  others = [node for node in policy.nodes if node.kind not in {"document", "section"}]
  nodes = [document, *cluster_nodes.values(), *sections, *others]
  return ViewGraph(nodes=nodes, edges=edges)
