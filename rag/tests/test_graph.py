from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from rag.retrieve import retrieve_graph
from rag.service import answer_question

from tests.conftest import hit


def _tiny_ir() -> GraphIR:
  return GraphIR(
    nodes=[
      GraphNode(
        id="DPDP_SEC_6_SUB_4",
        label="Obligation",
        properties={
          "title": "Withdrawal of consent",
          "text": "A Data Principal may withdraw her consent.",
          "act": "DPDP",
          "section_id": "DPDP_SEC_6",
        },
      ),
      GraphNode(
        id="DPDP_SEC_6_SUB_5",
        label="Obligation",
        properties={
          "title": "Consequences of withdrawal",
          "text": "Withdrawal does not affect prior lawful processing.",
          "act": "DPDP",
          "section_id": "DPDP_SEC_6",
        },
      ),
      GraphNode(
        id="DPDP_SEC_8_SUB_5",
        label="Obligation",
        properties={
          "title": "Reasonable security safeguards",
          "text": "Implement reasonable security safeguards.",
          "act": "DPDP",
          "section_id": "DPDP_SEC_8",
        },
      ),
      GraphNode(
        id="PEN_DPDP_33",
        label="Penalty",
        properties={"title": "Penalty", "act": "DPDP"},
      ),
    ],
    relationships=[
      GraphRelationship(source="PEN_DPDP_33", target="DPDP_SEC_6_SUB_4", type="PENALIZES"),
      GraphRelationship(source="PEN_DPDP_33", target="DPDP_SEC_6_SUB_5", type="PENALIZES"),
    ],
  )


def test_graph_expand_adds_penalizes_partner() -> None:
  def fake_search(query: str, *, source_type: str, top_k: int, min_score: float | None = None, **_):
    if source_type != "kg_obligation":
      return []
    return [
      hit(
        source_type="kg_obligation",
        cid="DPDP_SEC_6_SUB_4",
        obligation_id="DPDP_SEC_6_SUB_4",
        title="Withdrawal of consent",
        text="A Data Principal may withdraw her consent.",
      )
    ]

  citations = retrieve_graph("withdraw consent", search=fake_search, ir=_tiny_ir())
  ids = [row.id for row in citations]
  assert "DPDP_SEC_6_SUB_4" in ids
  assert "DPDP_SEC_6_SUB_5" in ids
  assert "DPDP_SEC_8_SUB_5" not in ids


def test_graph_expand_adds_same_section_neighbor() -> None:
  ir = GraphIR(
    nodes=[
      GraphNode(
        id="SPDI_RULE_5_SUB_7",
        label="Obligation",
        properties={
          "title": "Withdraw consent",
          "text": "Provider may withdraw consent in writing.",
          "act": "SPDI",
          "section_id": "SPDI_RULE_5",
        },
      ),
      GraphNode(
        id="SPDI_RULE_5_SUB_9",
        label="Obligation",
        properties={
          "title": "Grievance Officer",
          "text": "Designate a Grievance Officer.",
          "act": "SPDI",
          "section_id": "SPDI_RULE_5",
        },
      ),
    ],
    relationships=[],
  )

  def fake_search(query: str, *, source_type: str, top_k: int, min_score: float | None = None, **_):
    if source_type != "kg_obligation":
      return []
    return [
      hit(
        source_type="kg_obligation",
        cid="SPDI_RULE_5_SUB_7",
        obligation_id="SPDI_RULE_5_SUB_7",
        title="Withdraw consent",
        text="Provider may withdraw consent in writing.",
      )
    ]

  ids = [row.id for row in retrieve_graph("grievance", search=fake_search, ir=ir)]
  assert "SPDI_RULE_5_SUB_7" in ids
  assert "SPDI_RULE_5_SUB_9" in ids


def test_graph_expand_same_id_prefix_when_section_id_missing() -> None:
  ir = GraphIR(
    nodes=[
      GraphNode(
        id="DPDP_SEC_6_SUB_4",
        label="Obligation",
        properties={"title": "Withdraw", "text": "may withdraw", "act": "DPDP"},
      ),
      GraphNode(
        id="DPDP_SEC_6_SUB_5",
        label="Obligation",
        properties={"title": "Consequences", "text": "prior processing", "act": "DPDP"},
      ),
      GraphNode(
        id="DPDP_SEC_8_SUB_5",
        label="Obligation",
        properties={"title": "Security", "text": "safeguards", "act": "DPDP"},
      ),
    ],
    relationships=[],
  )

  def fake_search(query: str, *, source_type: str, top_k: int, min_score: float | None = None, **_):
    if source_type != "kg_obligation":
      return []
    return [
      hit(
        source_type="kg_obligation",
        cid="DPDP_SEC_6_SUB_4",
        obligation_id="DPDP_SEC_6_SUB_4",
        title="Withdraw",
        text="may withdraw",
      )
    ]

  ids = [row.id for row in retrieve_graph("withdraw", search=fake_search, ir=ir)]
  assert "DPDP_SEC_6_SUB_4" in ids
  assert "DPDP_SEC_6_SUB_5" in ids
  assert "DPDP_SEC_8_SUB_5" not in ids


def test_graph_falls_back_to_kg_section() -> None:
  ir = GraphIR(
    nodes=[
      GraphNode(
        id="ITACT_SEC_43A",
        label="Obligation",
        properties={"title": "43A", "text": "compensation", "act": "IT_ACT", "section_id": "ITACT_SEC_43A"},
      )
    ]
  )

  def fake_search(query: str, *, source_type: str, top_k: int, min_score: float | None = None, **_):
    if source_type == "kg_obligation":
      return []
    assert source_type == "kg_section"
    return [
      hit(
        source_type="kg_section",
        cid="ITACT_SEC_43A",
        section_id="ITACT_SEC_43A",
        title="Compensation",
        text="liable to pay damages by way of compensation",
      )
    ]

  citations = retrieve_graph("section 43A compensation", search=fake_search, ir=ir)
  assert citations[0].id == "ITACT_SEC_43A"


def test_graph_context_capped_at_eight() -> None:
  nodes = [
    GraphNode(
      id=f"DUTY_{i}",
      label="Obligation",
      properties={"title": f"Duty {i}", "text": f"text {i}", "act": "DPDP", "section_id": "SEC"},
    )
    for i in range(12)
  ]

  def fake_search(query: str, *, source_type: str, top_k: int, min_score: float | None = None, **_):
    if source_type != "kg_obligation":
      return []
    return [
      hit(
        source_type="kg_obligation",
        cid="DUTY_0",
        obligation_id="DUTY_0",
        title="Duty 0",
        text="text 0",
      )
    ]

  citations = retrieve_graph("duty", search=fake_search, ir=GraphIR(nodes=nodes))
  assert len(citations) == 8


def test_graph_answer_uses_stub_chat() -> None:
  def fake_search(query: str, *, source_type: str, top_k: int, min_score: float | None = None, **_):
    if source_type != "kg_obligation":
      return []
    return [
      hit(
        source_type="kg_obligation",
        cid="DPDP_SEC_6_SUB_4",
        obligation_id="DPDP_SEC_6_SUB_4",
        title="Withdrawal",
        text="A Data Principal may withdraw her consent.",
      )
    ]

  def fake_chat(system: str, user: str) -> str:
    assert "DPDP_SEC_6_SUB_4" in user
    return "Yes, consent may be withdrawn. Cited: DPDP_SEC_6_SUB_4"

  result = answer_question(
    "Can consent be withdrawn?",
    mode="graph",
    search=fake_search,
    chat=fake_chat,
    ir=_tiny_ir(),
  )
  assert result.mode == "graph"
  assert "withdraw" in result.answer.lower()
  assert {row.id for row in result.citations} >= {"DPDP_SEC_6_SUB_4", "DPDP_SEC_6_SUB_5"}
