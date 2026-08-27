from unittest.mock import MagicMock

import pytest

from vectorization.config import VectorizationSettings
from vectorization.models import clause_to_embeddable
from vectorization.store import VectorStore, l2_normalize, point_id

from tests.conftest import make_clause


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
  assert point.id == point_id(record.document_id, record.clause_id)
  assert point.vector == pytest.approx([0.6, 0.8, 0.0])
  assert point.payload["source_type"] == "document_clause"
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
