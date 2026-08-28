"""Project filtered law chunks into a Topic → LawChunk view graph."""

from __future__ import annotations

from collections import defaultdict

from policy_compare.models import LawChunk, ViewEdge, ViewGraph, ViewNode
from policy_compare.topics import topic_title


def project_ideal_graph(chunks: list[LawChunk]) -> ViewGraph:
  """Build one ideal graph: topic hubs with attached law chunks."""
  by_topic: dict[str, list[LawChunk]] = defaultdict(list)
  for chunk in chunks:
    for topic_id in chunk.topic_ids:
      by_topic[topic_id].append(chunk)

  nodes: list[ViewNode] = []
  edges: list[ViewEdge] = []
  seen_chunks: set[str] = set()

  for topic_id in sorted(by_topic):
    nodes.append(
      ViewNode(
        id=topic_id,
        kind="topic",
        title=topic_title(topic_id),
        summary="",
        status="missing",
      )
    )
    for chunk in by_topic[topic_id]:
      if chunk.doc_id not in seen_chunks:
        seen_chunks.add(chunk.doc_id)
        nodes.append(
          ViewNode(
            id=chunk.doc_id,
            kind="law_chunk",
            title=chunk.title,
            summary=chunk.summary,
            extra={"act": chunk.act, "chunk_type": chunk.chunk_type or ""},
          )
        )
      edges.append(
        ViewEdge(source=topic_id, target=chunk.doc_id, type="HAS_CHUNK"),
      )

  return ViewGraph(nodes=nodes, edges=edges)
