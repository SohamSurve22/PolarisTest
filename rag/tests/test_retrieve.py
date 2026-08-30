from rag.retrieve import citations_from_hits, retrieve_dense

from tests.conftest import hit


def test_dense_retrieve_uses_rag_section_top_k() -> None:
  seen: dict[str, object] = {}

  def fake_search(query: str, *, source_type: str, top_k: int, min_score: float | None = None, **_):
    seen["query"] = query
    seen["source_type"] = source_type
    seen["top_k"] = top_k
    return [
      hit(
        source_type="rag_section",
        cid="DPDP_SEC_6_SUB_5",
        title="Consent - Consequences of Withdrawal",
        text="Withdrawal does not invalidate prior processing.",
      )
    ]

  citations = retrieve_dense("Can a Data Principal withdraw consent?", search=fake_search)
  assert seen["source_type"] == "rag_section"
  assert seen["top_k"] == 5
  assert [row.id for row in citations] == ["DPDP_SEC_6_SUB_5"]
  assert citations[0].title == "Consent - Consequences of Withdrawal"
  assert "prior processing" in citations[0].text


def test_citations_from_hits_never_use_kg_obligation_for_dense() -> None:
  rows = citations_from_hits(
    [
      hit(source_type="rag_section", cid="ITACT_SEC_43A", text="compensation"),
      hit(
        source_type="kg_obligation",
        cid="DPDP_SEC_6_SUB_5",
        obligation_id="DPDP_SEC_6_SUB_5",
        text="should not appear in dense",
      ),
    ],
    allowed_source_types=("rag_section",),
  )
  assert [row.id for row in rows] == ["ITACT_SEC_43A"]
