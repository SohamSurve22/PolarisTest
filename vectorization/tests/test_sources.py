import json
from pathlib import Path

from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import Entity, EntityClause, EntityDocument, EntityType
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from tests.conftest import make_clause
from vectorization.chunking import sources_to_embeddable
from vectorization.sources import entity_document_to_sources, load_embeddable_sources


def _metadata() -> dict[str, str]:
  return {
    "document_id": "DOC_abc123",
    "filename": "test.txt",
    "format": "txt",
  }


def _clause_dict(**overrides: object) -> dict[str, object]:
  payload = make_clause().model_dump(mode="json")
  payload.update(overrides)
  return payload


def _write_doc(tmp_path: Path, payload: dict[str, object]) -> Path:
  path = tmp_path / "DOC_abc123.json"
  path.write_text(json.dumps(payload), encoding="utf-8")
  return tmp_path


def test_load_clauses_shape_matches_today(tmp_path: Path) -> None:
  _write_doc(
    tmp_path,
    {"metadata": _metadata(), "clauses": [_clause_dict()]},
  )
  sources = load_embeddable_sources(tmp_path)
  records = sources_to_embeddable(sources, min_tokens=5, max_tokens=512, overlap_tokens=50)

  assert len(records) == 1
  assert records[0].clause_id == "S001_C001"
  assert records[0].retrieval_text == (
    "Definitions — Personal data means any information relating to an identified person."
  )


def test_load_entity_clauses_unwraps_and_tags_entities(tmp_path: Path) -> None:
  clause = _clause_dict()
  _write_doc(
    tmp_path,
    {
      "metadata": _metadata(),
      "entity_clauses": [
        {
          "contextual_clause": {
            "classified_clause": {
              "clause": clause,
              "role": "STATEMENT",
            }
          },
          "entities": [
            {"entity_type": "ORGANIZATION"},
            {"entity_type": "DATE"},
            {"entity_type": "ORGANIZATION"},
          ],
        }
      ],
    },
  )
  sources = load_embeddable_sources(tmp_path)
  records = sources_to_embeddable(sources, min_tokens=5, max_tokens=512, overlap_tokens=50)

  assert len(records) == 1
  assert records[0].clause_id == "S001_C001"
  assert records[0].clause_text == clause["clause_text"]
  assert "(entities: ORGANIZATION, DATE)" in records[0].retrieval_text
  assert "(role:" not in records[0].retrieval_text


def test_in_memory_entity_document_becomes_embedding_sources() -> None:
  clause = make_clause()
  classified = ClassifiedClause(clause=clause, role=StructuralRole.STATEMENT)
  document = EntityDocument(
    metadata=DocumentMetadata(document_id="DOC_memory", filename="policy.txt", format=DocumentFormat.TXT),
    entity_clauses=[
      EntityClause(
        contextual_clause=ContextualClause(classified_clause=classified),
        entities=[Entity(entity_type=EntityType.ORGANIZATION)],
      ),
    ],
  )

  sources = entity_document_to_sources(document)

  assert len(sources) == 1
  assert sources[0].clause.clause_id == clause.clause_id
  assert sources[0].entity_types == ["ORGANIZATION"]


def test_load_contextual_heading_tags_role(tmp_path: Path) -> None:
  _write_doc(
    tmp_path,
    {
      "metadata": _metadata(),
      "contextual_clauses": [
        {
          "classified_clause": {
            "clause": _clause_dict(
              clause_text="Control over your information settings here now",
            ),
            "role": "HEADING",
          }
        }
      ],
    },
  )
  sources = load_embeddable_sources(tmp_path)
  records = sources_to_embeddable(sources, min_tokens=5, max_tokens=512, overlap_tokens=50)

  assert len(records) == 1
  assert "(role: HEADING)" in records[0].retrieval_text


def test_malformed_nested_item_skipped_siblings_kept(tmp_path: Path) -> None:
  good = _clause_dict(clause_id="S001_C002")
  _write_doc(
    tmp_path,
    {
      "metadata": _metadata(),
      "entity_clauses": [
        {"entities": []},
        {
          "contextual_clause": {
            "classified_clause": {"clause": good, "role": "STATEMENT"}
          },
          "entities": [],
        },
      ],
    },
  )
  sources = load_embeddable_sources(tmp_path)
  records = sources_to_embeddable(sources, min_tokens=5, max_tokens=512, overlap_tokens=50)

  assert [record.clause_id for record in records] == ["S001_C002"]


def test_short_heading_still_skipped(tmp_path: Path) -> None:
  _write_doc(
    tmp_path,
    {
      "metadata": _metadata(),
      "contextual_clauses": [
        {
          "classified_clause": {
            "clause": _clause_dict(clause_text="a b c"),
            "role": "HEADING",
          }
        }
      ],
    },
  )
  sources = load_embeddable_sources(tmp_path)
  records = sources_to_embeddable(sources, min_tokens=5, max_tokens=512, overlap_tokens=50)

  assert records == []
