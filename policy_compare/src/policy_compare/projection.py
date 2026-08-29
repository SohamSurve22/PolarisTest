"""Project filtered law chunks into Ideal → statute → theme → topic → chunk."""

from __future__ import annotations

from collections import defaultdict

from policy_compare.models import LawChunk, ViewEdge, ViewGraph, ViewNode
from policy_compare.topics import (
  statute_key,
  statute_title,
  theme_for_topic,
  theme_title,
  topic_title,
)

IDEAL_HUB_ID = "cluster:ideal"


def project_ideal_graph(chunks: list[LawChunk]) -> ViewGraph:
  """Build the ideal tree: hub, statute clusters, themes, per-act topics, chunks."""
  by_act_topic: dict[tuple[str, str], list[LawChunk]] = defaultdict(list)
  for chunk in chunks:
    act = statute_key(chunk.act)
    for topic_id in chunk.topic_ids:
      by_act_topic[(act, topic_id)].append(chunk)

  nodes: list[ViewNode] = [
    ViewNode(
      id=IDEAL_HUB_ID,
      kind="cluster",
      title="Ideal policy",
      summary="Topics a private-company website privacy policy should cover.",
      extra={"role": "ideal_hub"},
    ),
  ]
  edges: list[ViewEdge] = []
  seen_statutes: set[str] = set()
  seen_themes: set[str] = set()
  seen_chunks: set[str] = set()

  for (act, topic_id), topic_chunks in sorted(by_act_topic.items()):
    statute_id = f"cluster:statute:{act}"
    if act not in seen_statutes:
      seen_statutes.add(act)
      nodes.append(
        ViewNode(
          id=statute_id,
          kind="cluster",
          title=statute_title(act),
          extra={"role": "statute", "act": act},
        )
      )
      edges.append(ViewEdge(source=IDEAL_HUB_ID, target=statute_id, type="CONTAINS"))

    theme = theme_for_topic(topic_id)
    theme_id = f"cluster:{act}:{theme}"
    if theme_id not in seen_themes:
      seen_themes.add(theme_id)
      nodes.append(
        ViewNode(
          id=theme_id,
          kind="cluster",
          title=theme_title(theme),
          extra={"role": "theme", "act": act, "theme": theme},
        )
      )
      edges.append(ViewEdge(source=statute_id, target=theme_id, type="CONTAINS"))

    scoped_topic = f"{topic_id}@{act}"
    nodes.append(
      ViewNode(
        id=scoped_topic,
        kind="topic",
        title=topic_title(topic_id),
        summary="",
        status="missing",
        extra={"topic_id": topic_id, "act": act},
      )
    )
    edges.append(ViewEdge(source=theme_id, target=scoped_topic, type="CONTAINS"))

    for chunk in topic_chunks:
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
      edges.append(ViewEdge(source=scoped_topic, target=chunk.doc_id, type="HAS_CHUNK"))

  return ViewGraph(nodes=nodes, edges=edges)
