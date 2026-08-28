from pathlib import Path
from unittest.mock import MagicMock, patch

from vectorization.config import VectorizationSettings
from vectorization.kg import kg_file_to_records, load_kg_records
from vectorization.models import clause_to_embeddable
from vectorization.store import VectorStore, record_point_id

from tests.conftest import make_clause


def _settings(**overrides: object) -> VectorizationSettings:
  values: dict[str, object] = {
    "qdrant_url": "http://localhost:6333",
    "qdrant_collection": "document_clauses",
    "embedding_model": "nomic-embed-text",
    "embedding_dim": 3,
    "kg_max_tokens": 300,
    "chunk_overlap_tokens": 50,
  }
  values.update(overrides)
  return VectorizationSettings.model_validate(values)


def _kg_payload(**overrides: object) -> dict[str, object]:
  payload: dict[str, object] = {
    "law_code": "DPDPA-2023",
    "language": "en",
    "sections": [
      {
        "section_id": "S8",
        "title": "Data principal rights",
        "text": "A Data Principal shall have the right to access personal data.",
      }
    ],
    "obligations": [
      {
        "obligation_id": "obl_S8_0",
        "section_id": "S8",
        "text": "The Data Fiduciary shall allow a Data Principal to access their personal data.",
      }
    ],
  }
  payload.update(overrides)
  return payload


def test_kg_file_to_records_sets_obligation_payload_fields() -> None:
  records = kg_file_to_records(_kg_payload(), max_tokens=300, overlap_tokens=50)
  obligation = next(record for record in records if record.source_type == "kg_obligation")

  assert obligation.law_code == "DPDPA-2023"
  assert obligation.obligation_id == "obl_S8_0"
  assert obligation.section_id == "S8"
  assert obligation.document_id is None
  assert obligation.clause_id is None
  assert obligation.source["chunk_type"] == "obligation_text"
  assert "Data Fiduciary" in obligation.retrieval_text


def test_kg_section_prefixes_title() -> None:
  records = kg_file_to_records(_kg_payload(), max_tokens=300, overlap_tokens=50)
  section = next(record for record in records if record.source_type == "kg_section")

  assert section.retrieval_text.startswith("Data principal rights — ")
  assert section.source["chunk_type"] == "section_text"


def test_kg_skips_empty_text() -> None:
  records = kg_file_to_records(
    _kg_payload(
      obligations=[{"obligation_id": "obl_empty", "text": "   "}],
      sections=[],
    ),
    max_tokens=300,
    overlap_tokens=50,
  )
  assert records == []


def test_kg_long_obligation_splits_into_distinct_point_ids() -> None:
  para_a = " ".join(f"alpha{i}" for i in range(200))
  para_b = " ".join(f"beta{i}" for i in range(200))
  records = kg_file_to_records(
    _kg_payload(
      sections=[],
      obligations=[
        {
          "obligation_id": "obl_long",
          "section_id": "S8",
          "text": f"{para_a}\n\n{para_b}",
        }
      ],
    ),
    max_tokens=300,
    overlap_tokens=50,
  )

  assert len(records) >= 2
  assert {record.obligation_id for record in records} == {"obl_long"}
  ids = [record_point_id(record) for record in records]
  assert len(set(ids)) == len(ids)


def test_load_kg_records_from_directory(tmp_path: Path) -> None:
  fixture = Path(__file__).parent / "fixtures" / "kg_sample.json"
  (tmp_path / "dpdpa.json").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
  records = load_kg_records(tmp_path, max_tokens=300, overlap_tokens=50)
  assert any(record.source_type == "kg_obligation" for record in records)


def test_upsert_kg_obligation_payload() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  store = VectorStore(_settings(), client=client)
  record = kg_file_to_records(
    _kg_payload(sections=[]),
    max_tokens=300,
    overlap_tokens=50,
  )[0]

  store.upsert_batch([record], [[3.0, 4.0, 0.0]])

  point = client.upsert.call_args.kwargs["points"][0]
  assert point.id == record_point_id(record)
  assert point.payload["source_type"] == "kg_obligation"
  assert point.payload["law_code"] == "DPDPA-2023"
  assert point.payload["obligation_id"] == "obl_S8_0"
  assert point.payload["document_id"] is None
  assert point.payload["chunk_type"] == "obligation_text"


def test_document_upsert_still_document_clause() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  store = VectorStore(_settings(), client=client)
  record = clause_to_embeddable(make_clause())

  store.upsert_batch([record], [[3.0, 4.0, 0.0]])

  point = client.upsert.call_args.kwargs["points"][0]
  assert point.payload["source_type"] == "document_clause"
  assert point.payload["document_id"] == "DOC_abc123"


def test_search_can_filter_kg_obligation() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  client.query_points.return_value = MagicMock(points=[])
  store = VectorStore(_settings(), client=client)

  store.search([1.0, 0.0, 0.0], source_type="kg_obligation")

  query_filter = client.query_points.call_args.kwargs["query_filter"]
  values = {condition.key: condition.match.value for condition in query_filter.must}
  assert values["source_type"] == "kg_obligation"


@patch("vectorization.cli.run_kg")
def test_cli_ingest_kg_calls_run_kg(mock_run_kg: MagicMock) -> None:
  from vectorization.cli import main

  assert main(["ingest-kg"]) == 0
  mock_run_kg.assert_called_once()
