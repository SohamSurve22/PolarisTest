"""Score policy sections against ideal topics with lexical overlap."""

from __future__ import annotations

from policy_compare.models import LawChunk, MatchLink, MatchResult, ViewGraph, ViewNode
from policy_compare.topics import TOPIC_KEYWORDS

COVERED_MIN = 0.55
WEAK_MIN = 0.30


def _score(text: str, topic_id: str, chunks: list[LawChunk]) -> float:
  haystack = text.lower()
  keywords = list(TOPIC_KEYWORDS.get(topic_id, ()))
  for chunk in chunks:
    keywords.extend(chunk.title.lower().split()[:6])
  unique = {key.strip() for key in keywords if len(key.strip()) >= 4}
  if not unique:
    return 0.0
  hits = sum(1 for key in unique if key in haystack)
  return min(1.0, hits / 3.0)


def match_graphs(
  policy: ViewGraph,
  ideal: ViewGraph,
  chunks: list[LawChunk],
) -> MatchResult:
  """Annotate policy and ideal graphs with overlay statuses."""
  chunks_by_topic: dict[str, list[LawChunk]] = {}
  for chunk in chunks:
    for topic_id in chunk.topic_ids:
      chunks_by_topic.setdefault(topic_id, []).append(chunk)

  topic_nodes = [node for node in ideal.nodes if node.kind == "topic"]
  section_nodes = [node for node in policy.nodes if node.kind == "section"]

  links: list[MatchLink] = []
  best_for_topic: dict[str, float] = {node.id: 0.0 for node in topic_nodes}
  mapped_sections: set[str] = set()

  for section in section_nodes:
    text = f"{section.title} {section.summary}"
    for topic in topic_nodes:
      score = _score(text, topic.id, chunks_by_topic.get(topic.id, []))
      if score >= WEAK_MIN:
        links.append(
          MatchLink(
            policy_section_id=section.id,
            topic_id=topic.id,
            score=round(score, 3),
          )
        )
        best_for_topic[topic.id] = max(best_for_topic[topic.id], score)
        mapped_sections.add(section.id)

  policy_nodes: list[ViewNode] = []
  for node in policy.nodes:
    if node.kind != "section":
      policy_nodes.append(node)
      continue
    status = "mapped" if node.id in mapped_sections else "extra"
    policy_nodes.append(node.model_copy(update={"status": status}))

  ideal_nodes: list[ViewNode] = []
  for node in ideal.nodes:
    if node.kind != "topic":
      ideal_nodes.append(node)
      continue
    score = best_for_topic.get(node.id, 0.0)
    if score >= COVERED_MIN:
      status = "covered"
    elif score >= WEAK_MIN:
      status = "weak"
    else:
      status = "missing"
    ideal_nodes.append(node.model_copy(update={"status": status}))

  return MatchResult(
    policy=ViewGraph(nodes=policy_nodes, edges=policy.edges),
    ideal=ViewGraph(nodes=ideal_nodes, edges=ideal.edges),
    links=links,
  )
