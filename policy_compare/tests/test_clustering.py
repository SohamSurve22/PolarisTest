from policy_compare.clustering import cluster_policy_graph
from policy_compare.models import MatchLink, ViewGraph, ViewNode


def _section(section_id: str, title: str, *, parent: str = "", status: str = "mapped") -> ViewNode:
  return ViewNode(
    id=f"section:{section_id}",
    kind="section",
    title=title,
    status=status,  # type: ignore[arg-type]
    extra={"section_id": section_id, "parent_section_id": parent},
  )


def test_top_level_mapped_section_hangs_off_topic_cluster() -> None:
  policy = ViewGraph(
    nodes=[
      ViewNode(id="doc:x", kind="document", title="Policy"),
      _section("S002", "Consent"),
    ],
  )
  graph = cluster_policy_graph(
    policy,
    [MatchLink(policy_section_id="section:S002", topic_id="TOPIC_CONSENT@TINY", score=0.9)],
  )
  cluster = next(node for node in graph.nodes if node.id == "cluster:policy:TOPIC_CONSENT")
  assert cluster.title == "Consent"
  assert any(edge.source == "doc:x" and edge.target == cluster.id for edge in graph.edges)
  assert any(edge.source == cluster.id and edge.target == "section:S002" for edge in graph.edges)


def test_extra_cluster_for_unmapped_top_level() -> None:
  policy = ViewGraph(
    nodes=[
      ViewNode(id="doc:x", kind="document", title="Policy"),
      _section("S009", "Blog", status="extra"),
    ],
  )
  graph = cluster_policy_graph(policy, [])
  assert any(node.id == "cluster:extra" for node in graph.nodes)
  assert any(edge.source == "cluster:extra" and edge.target == "section:S009" for edge in graph.edges)


def test_nested_section_attaches_to_parent() -> None:
  policy = ViewGraph(
    nodes=[
      ViewNode(id="doc:x", kind="document", title="Policy"),
      _section("S001", "Rights"),
      _section("S002", "Delete", parent="S001"),
    ],
  )
  graph = cluster_policy_graph(
    policy,
    [MatchLink(policy_section_id="section:S001", topic_id="TOPIC_USER_RIGHTS@DPDP", score=0.8)],
  )
  assert any(
    edge.source == "section:S001" and edge.target == "section:S002" for edge in graph.edges
  )
  assert not any(
    edge.target == "section:S002" and edge.source.startswith("cluster:") for edge in graph.edges
  )
