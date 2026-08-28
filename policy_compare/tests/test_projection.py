from pathlib import Path

from policy_compare.law_loader import load_law_chunks
from policy_compare.projection import project_ideal_graph

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_law.json"


def test_ideal_graph_has_consent_topic_and_chunk() -> None:
  chunks = load_law_chunks([FIXTURE])
  graph = project_ideal_graph(chunks)
  kinds = {node.kind for node in graph.nodes}
  assert kinds == {"topic", "law_chunk"}
  titles = {node.title for node in graph.nodes if node.kind == "topic"}
  assert titles == {"Consent"}
  assert any(node.id == "TINY_CONSENT" for node in graph.nodes)
  assert any(edge.type == "HAS_CHUNK" for edge in graph.edges)
