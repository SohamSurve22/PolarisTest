from pathlib import Path
from unittest.mock import MagicMock, patch

from vectorization.config import VectorizationSettings
from vectorization.models import EmbeddableRecord
from vectorization.store import VectorStore, record_point_id

from vectorization.kg import kg_file_to_records

FIXTURE = Path(__file__).parent / "fixtures" / "rag_merged_slice.json"
MERGED = Path(__file__).resolve().parents[2] / "dataset" / "IT_ACT_POLARISLEX_MERGED.json"


def _settings(**overrides: object) -> VectorizationSettings:
  values: dict[str, object] = {
    "qdrant_url": "http://localhost:6333",
    "qdrant_collection": "document_clauses",
    "embedding_model": "nomic-embed-text",
    "embedding_dim": 3,
  }
  values.update(overrides)
  return VectorizationSettings.model_validate(values)


def test_merged_slice_loads_rag_section_records() -> None:
  from vectorization.rag_corpus import load_rag_records

  records = load_rag_records(FIXTURE)
  ids = [record.clause_id for record in records]
  assert ids == ["DPDP_SEC_6_SUB_5", "ITACT_SEC_43A"]
  first = records[0]
  assert first.source_type == "rag_section"
  assert first.obligation_id == "DPDP_SEC_6_SUB_5"
  assert first.law_code == "DPDP"
  assert first.retrieval_text.startswith("Section 6 subsection 5")
  assert first.source["title"] == "Consent - Consequences of Withdrawal"
  assert first.source["topics"] == ["consent", "user_rights"]


def test_empty_retrieval_text_falls_back_to_clause_text() -> None:
  from vectorization.rag_corpus import load_rag_records

  records = load_rag_records(FIXTURE)
  itact = next(record for record in records if record.clause_id == "ITACT_SEC_43A")
  assert "reasonable security" in itact.retrieval_text


def test_merged_file_has_291_rag_section_records() -> None:
  from vectorization.rag_corpus import load_rag_records

  if not MERGED.is_file():
    raise AssertionError(f"merged corpus missing: {MERGED}")
  records = load_rag_records(MERGED)
  assert len(records) == 291
  assert all(record.source_type == "rag_section" for record in records)
  assert all(record.source_type != "kg_obligation" for record in records)
  assert {record.clause_id for record in records} >= {
    "DPDP_SEC_6_SUB_5",
    "ITACT_SEC_43A",
    "CERTIN_DIR_2",
  }


def test_rag_section_point_id_is_disjoint_from_kg_obligation() -> None:
  rag = EmbeddableRecord(
    clause_id="DPDP_SEC_6_SUB_5",
    obligation_id="DPDP_SEC_6_SUB_5",
    clause_text="x",
    retrieval_text="x",
    source_type="rag_section",
    law_code="DPDP",
    source={"chunk_index": 0, "chunk_type": "rag_section"},
  )
  kg = kg_file_to_records(
    {
      "law_code": "DPDP",
      "language": "en",
      "sections": [],
      "obligations": [
        {
          "obligation_id": "DPDP_SEC_6_SUB_5",
          "section_id": "DPDP_SEC_6_SUB_5",
          "text": "The Data Fiduciary shall allow withdrawal of consent.",
        }
      ],
    },
    max_tokens=300,
    overlap_tokens=50,
  )[0]
  document = EmbeddableRecord(
    clause_id="DPDP_SEC_6_SUB_5",
    document_id=None,
    clause_text="x",
    retrieval_text="x",
    source_type="document_clause",
    source={"chunk_index": 0},
  )
  assert record_point_id(rag) != record_point_id(kg)
  assert record_point_id(rag) != record_point_id(document)
  assert record_point_id(rag) == record_point_id(rag)


def test_upsert_rag_section_payload_keeps_title_and_topics() -> None:
  from vectorization.rag_corpus import load_rag_records

  client = MagicMock()
  client.collection_exists.return_value = True
  store = VectorStore(_settings(), client=client)
  record = load_rag_records(FIXTURE)[0]

  store.upsert_batch([record], [[3.0, 4.0, 0.0]])

  point = client.upsert.call_args.kwargs["points"][0]
  assert point.id == record_point_id(record)
  assert point.payload["source_type"] == "rag_section"
  assert point.payload["clause_id"] == "DPDP_SEC_6_SUB_5"
  assert point.payload["obligation_id"] == "DPDP_SEC_6_SUB_5"
  assert point.payload["law_code"] == "DPDP"
  assert point.payload["title"] == "Consent - Consequences of Withdrawal"
  assert point.payload["topics"] == ["consent", "user_rights"]


def test_search_rag_section_filter_does_not_use_kg_obligation() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  client.query_points.return_value = MagicMock(points=[])
  store = VectorStore(_settings(), client=client)

  store.search([1.0, 0.0, 0.0], source_type="rag_section")

  query_filter = client.query_points.call_args.kwargs["query_filter"]
  values = {condition.key: condition.match.value for condition in query_filter.must}
  assert values["source_type"] == "rag_section"
  assert values["source_type"] != "kg_obligation"


@patch("vectorization.cli.run_rag")
def test_cli_ingest_rag_calls_run_rag(mock_run_rag: MagicMock) -> None:
  from vectorization.cli import main

  assert main(["ingest-rag", "--path", str(FIXTURE)]) == 0
  mock_run_rag.assert_called_once()
  kwargs = mock_run_rag.call_args.kwargs
  assert kwargs.get("path") == Path(FIXTURE) or (
    mock_run_rag.call_args.args and mock_run_rag.call_args.args[-1] == Path(FIXTURE)
  )
