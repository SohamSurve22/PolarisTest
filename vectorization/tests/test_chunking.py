from vectorization.chunking import clauses_to_embeddable, token_count
from vectorization.models import clause_to_embeddable

from tests.conftest import make_clause


def _words(count: int, stem: str = "word") -> str:
  return " ".join(f"{stem}{i}" for i in range(count))


def test_token_count_is_whitespace_split() -> None:
  assert token_count("a b c") == 3
  assert token_count("  a   b  ") == 2


def test_clauses_to_embeddable_skips_short_clause() -> None:
  records = clauses_to_embeddable(
    [make_clause(clause_text="a b c")],
    min_tokens=5,
    max_tokens=512,
    overlap_tokens=50,
  )

  assert records == []


def test_clauses_to_embeddable_keeps_min_token_clause() -> None:
  records = clauses_to_embeddable(
    [make_clause(clause_text="one two three four five")],
    min_tokens=5,
    max_tokens=512,
    overlap_tokens=50,
  )

  assert len(records) == 1
  assert records[0].source["chunk_index"] == 0
  assert records[0].retrieval_text.endswith("one two three four five")


def test_section_title_does_not_count_toward_skip() -> None:
  records = clauses_to_embeddable(
    [make_clause(section_title=_words(20, "title"), clause_text="a b c")],
    min_tokens=5,
    max_tokens=512,
    overlap_tokens=50,
  )

  assert records == []


def test_long_clause_splits_with_overlap_and_stable_clause_id() -> None:
  first = _words(400, "aaa")
  second = _words(200, "bbb")
  clause = make_clause(clause_text=f"{first}. {second}.")

  records = clauses_to_embeddable(
    [clause],
    min_tokens=5,
    max_tokens=512,
    overlap_tokens=50,
  )

  assert len(records) >= 2
  assert {record.clause_id for record in records} == {"S001_C001"}
  indexes = [record.source["chunk_index"] for record in records]
  assert indexes == list(range(len(records)))
  for record in records:
    chunk_text = record.retrieval_text.split(" — ", 1)[-1]
    assert token_count(chunk_text) <= 512
    assert record.clause_text == clause.clause_text

  first_chunk = records[0].retrieval_text.split(" — ", 1)[-1]
  second_chunk = records[1].retrieval_text.split(" — ", 1)[-1]
  overlap = " ".join(first_chunk.split()[-50:])
  assert second_chunk.startswith(overlap)


def test_clause_to_embeddable_sets_chunk_index_zero() -> None:
  record = clause_to_embeddable(make_clause())

  assert record.source["chunk_index"] == 0
