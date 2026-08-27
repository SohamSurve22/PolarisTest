from unittest.mock import MagicMock

import pytest

from vectorization.config import VectorizationSettings
from vectorization.models import clause_to_embeddable
from vectorization.store import VectorStore, l2_normalize, point_id

from tests.conftest import make_clause


def _filter_match_values(query_filter: object) -> dict[str, object]:
  return {condition.key: condition.match.value for condition in query_filter.must}


def _settings(**overrides: object) -> VectorizationSettings:
  values: dict[str, object] = {
    "qdrant_url": "http://localhost:6333",
    "qdrant_collection": "document_clauses",
    "embedding_model": "nomic-embed-text",
    "embedding_dim": 3,
  }
  values.update(overrides)
  return VectorizationSettings.model_validate(values)


def test_point_id_is_stable_for_same_clause() -> None:
  first = point_id("DOC_abc123", "S001_C001")
  second = point_id("DOC_abc123", "S001_C001")

  assert first == second
  assert first != point_id("DOC_abc123", "S001_C002")


def test_point_id_differs_by_chunk_index() -> None:
  zero = point_id("DOC_abc123", "S001_C001", 0)
  one = point_id("DOC_abc123", "S001_C001", 1)

  assert zero != one
  assert zero == point_id("DOC_abc123", "S001_C001", 0)


def test_l2_normalize_unit_length() -> None:
  normalized = l2_normalize([3.0, 4.0, 0.0])

  assert normalized == pytest.approx([0.6, 0.8, 0.0])


def test_upsert_batch_creates_collection_when_missing() -> None:
  client = MagicMock()
  client.collection_exists.return_value = False

  VectorStore(_settings(), client=client)

  client.create_collection.assert_called_once()
  _, kwargs = client.create_collection.call_args
  assert kwargs["collection_name"] == "document_clauses"


def test_upsert_batch_sends_document_clause_payload() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  store = VectorStore(_settings(), client=client)
  record = clause_to_embeddable(make_clause())

  store.upsert_batch([record], [[3.0, 4.0, 0.0]])

  client.upsert.assert_called_once()
  _, kwargs = client.upsert.call_args
  assert kwargs["collection_name"] == "document_clauses"
  point = kwargs["points"][0]
  assert point.id == point_id(record.document_id, record.clause_id, 0)
  assert point.vector == pytest.approx([0.6, 0.8, 0.0])
  assert point.payload["source_type"] == "document_clause"
  assert point.payload["chunk_index"] == 0
  assert point.payload["document_id"] == "DOC_abc123"
  assert point.payload["clause_id"] == "S001_C001"
  assert point.payload["section_id"] == "S001"
  assert point.payload["embedding_model_version"] == "nomic-embed-text"
  assert point.payload["language"] == "en"
  assert point.payload["retrieval_text"] == record.retrieval_text


def test_upsert_batch_rejects_dimension_mismatch() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  store = VectorStore(_settings(embedding_dim=3), client=client)
  record = clause_to_embeddable(make_clause())

  with pytest.raises(ValueError, match="dimension"):
    store.upsert_batch([record], [[1.0, 0.0]])


def test_upsert_batch_uses_chunk_index_in_point_id() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  store = VectorStore(_settings(), client=client)
  record = clause_to_embeddable(make_clause())
  record.source["chunk_index"] = 1

  store.upsert_batch([record], [[3.0, 4.0, 0.0]])

  point = client.upsert.call_args.kwargs["points"][0]
  assert point.id == point_id(record.document_id, record.clause_id, 1)
  assert point.payload["chunk_index"] == 1


def _scored_point(score: float, **payload: object) -> MagicMock:
  point = MagicMock()
  point.score = score
  point.payload = {
    "source_type": "document_clause",
    "document_id": "DOC_abc123",
    "clause_id": "S001_C001",
    "section_id": "S001",
    "clause_text": "Personal data means any information.",
    "retrieval_text": "Definitions — Personal data means any information.",
    "embedding_model_version": "nomic-embed-text",
    **payload,
  }
  return point


def test_search_sends_unit_query_and_model_filters() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  client.query_points.return_value = MagicMock(points=[_scored_point(0.9)])
  store = VectorStore(_settings(), client=client)

  hits = store.search([3.0, 4.0, 0.0], top_k=5, min_score=0.55)

  client.query_points.assert_called_once()
  _, kwargs = client.query_points.call_args
  assert kwargs["collection_name"] == "document_clauses"
  assert kwargs["query"] == pytest.approx([0.6, 0.8, 0.0])
  assert kwargs["limit"] == 5
  assert _filter_match_values(kwargs["query_filter"]) == {
    "source_type": "document_clause",
    "embedding_model_version": "nomic-embed-text",
  }
  assert len(hits) == 1
  assert hits[0].score == 0.9
  assert hits[0].clause_id == "S001_C001"
  assert hits[0].retrieval_text == "Definitions — Personal data means any information."
  assert hits[0].payload["document_id"] == "DOC_abc123"


def test_search_adds_document_id_filter_when_provided() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  client.query_points.return_value = MagicMock(points=[])
  store = VectorStore(_settings(), client=client)

  store.search([1.0, 0.0, 0.0], document_id="DOC_abc123")

  _, kwargs = client.query_points.call_args
  assert _filter_match_values(kwargs["query_filter"])["document_id"] == "DOC_abc123"


def test_search_drops_hits_below_min_score() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  client.query_points.return_value = MagicMock(
    points=[
      _scored_point(0.9, clause_id="keep"),
      _scored_point(0.4, clause_id="drop"),
    ]
  )
  store = VectorStore(_settings(), client=client)

  hits = store.search([1.0, 0.0, 0.0], min_score=0.55)

  assert [hit.clause_id for hit in hits] == ["keep"]


def test_search_rejects_dimension_mismatch() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  store = VectorStore(_settings(embedding_dim=3), client=client)

  with pytest.raises(ValueError, match="dimension"):
    store.search([1.0, 0.0])
