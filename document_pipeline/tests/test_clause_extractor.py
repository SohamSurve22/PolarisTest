"""Tests for Stage 6: ClauseExtractor (refactored — consumes ClauseCandidateDocument)."""

from document_pipeline.clause_segmentation.sentence_splitter import SentenceSplitter
from document_pipeline.models.candidate import ClauseCandidate, ClauseCandidateDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.stages.clause_extractor import ClauseExtractor


def _make_candidate(
  text: str,
  *,
  candidate_id: str = "S001_P001",
  section_id: str = "S001",
  order: int = 0,
  section_title: str | None = None,
) -> ClauseCandidate:
  meta: dict[str, object] = {}
  if section_title:
    meta["section_title"] = section_title
  return ClauseCandidate(
    candidate_id=candidate_id,
    section_id=section_id,
    block_ids=[f"{section_id}_B001"],
    text=text,
    order=order,
    metadata=meta,
  )


def _make_candidate_doc(
  candidates: list[ClauseCandidate],
  document_id: str = "doc-clause-001",
) -> ClauseCandidateDocument:
  metadata = DocumentMetadata(
    document_id=document_id,
    filename="agreement.txt",
    format=DocumentFormat.TXT,
  )
  return ClauseCandidateDocument(metadata=metadata, candidates=candidates)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_extractor_splits_single_sentence_clause(
  clause_extractor: ClauseExtractor,
) -> None:
  text = "The Partner shall maintain confidentiality."
  candidate_doc = _make_candidate_doc([_make_candidate(text)])

  segmented = clause_extractor.process(candidate_doc)

  assert len(segmented.clauses) == 1
  clause = segmented.clauses[0]
  assert clause.clause_id == "S001_C001"
  assert clause.clause_text == text
  assert clause.section_id == "S001"
  assert clause.document_id == "doc-clause-001"
  assert clause.document_type == DocumentFormat.TXT


def test_extractor_splits_multi_sentence_paragraph(
  clause_extractor: ClauseExtractor,
) -> None:
  text = "The Partner shall comply. The Partner shall report breaches."
  candidate_doc = _make_candidate_doc([_make_candidate(text)])

  segmented = clause_extractor.process(candidate_doc)

  assert [clause.clause_text for clause in segmented.clauses] == [
    "The Partner shall comply.",
    "The Partner shall report breaches.",
  ]
  assert [clause.clause_id for clause in segmented.clauses] == ["S001_C001", "S001_C002"]


def test_extractor_handles_abbreviations(
  clause_extractor: ClauseExtractor,
) -> None:
  text = "Terms apply per Sec. 12, e.g., notice periods. Dr. Smith must approve."
  candidate_doc = _make_candidate_doc([_make_candidate(text)])

  segmented = clause_extractor.process(candidate_doc)

  assert len(segmented.clauses) == 2
  assert segmented.clauses[0].clause_text == "Terms apply per Sec. 12, e.g., notice periods."
  assert segmented.clauses[1].clause_text == "Dr. Smith must approve."


def test_extractor_treats_numbered_list_items_as_clauses(
  clause_extractor: ClauseExtractor,
) -> None:
  text = "1. Provide notice.\n2. Maintain records."
  candidate_doc = _make_candidate_doc([_make_candidate(text)])

  segmented = clause_extractor.process(candidate_doc)

  assert len(segmented.clauses) == 2
  assert segmented.clauses[0].clause_text == "1. Provide notice."
  assert segmented.clauses[0].clause_number == "1."
  assert segmented.clauses[1].clause_text == "2. Maintain records."
  assert segmented.clauses[1].clause_number == "2."


def test_extractor_treats_bullet_list_items_as_clauses(
  clause_extractor: ClauseExtractor,
) -> None:
  text = "- Provide notice.\n- Maintain records."
  candidate_doc = _make_candidate_doc([_make_candidate(text)])

  segmented = clause_extractor.process(candidate_doc)

  assert len(segmented.clauses) == 2
  assert segmented.clauses[0].clause_number == "-"
  assert segmented.clauses[0].clause_text == "- Provide notice."
  assert segmented.clauses[1].clause_text == "- Maintain records."


def test_extractor_preserves_candidate_relative_character_offsets(
  clause_extractor: ClauseExtractor,
) -> None:
  text = "First sentence. Second sentence."
  candidate_doc = _make_candidate_doc([_make_candidate(text)])

  segmented = clause_extractor.process(candidate_doc)

  for clause in segmented.clauses:
    assert text[clause.span.start : clause.span.end] == clause.clause_text


def test_extractor_maps_clauses_to_parent_sections(
  clause_extractor: ClauseExtractor,
) -> None:
  candidates = [
    _make_candidate("Alpha sentence.", candidate_id="S001_P001", section_id="S001",
                     order=0, section_title="Alpha"),
    _make_candidate("Beta sentence.", candidate_id="S002_P001", section_id="S002",
                     order=1, section_title="Beta"),
  ]
  candidate_doc = _make_candidate_doc(candidates)

  segmented = clause_extractor.process(candidate_doc)

  assert [clause.section_id for clause in segmented.clauses] == ["S001", "S002"]
  assert [clause.section_title for clause in segmented.clauses] == ["Alpha", "Beta"]
  assert [clause.clause_id for clause in segmented.clauses] == ["S001_C001", "S002_C001"]


def test_extractor_restarts_clause_numbering_per_section(
  clause_extractor: ClauseExtractor,
) -> None:
  candidates = [
    _make_candidate(
      "First sentence. Second sentence.",
      candidate_id="S001_P001", section_id="S001", order=0,
    ),
    _make_candidate(
      "Third sentence.",
      candidate_id="S002_P001", section_id="S002", order=1,
    ),
  ]
  candidate_doc = _make_candidate_doc(candidates)

  segmented = clause_extractor.process(candidate_doc)

  assert [clause.clause_id for clause in segmented.clauses] == [
    "S001_C001",
    "S001_C002",
    "S002_C001",
  ]


def test_extractor_is_deterministic_and_idempotent(
  clause_extractor: ClauseExtractor,
) -> None:
  text = "1. Provide notice.\n- Bullet item."
  candidate_doc = _make_candidate_doc([_make_candidate(text)])

  first = clause_extractor.process(candidate_doc)
  second = clause_extractor.process(candidate_doc)

  assert first == second


def test_clause_accepts_legacy_text_field() -> None:
  from document_pipeline.models.clause import Clause

  clause = Clause.model_validate(
    {
      "clause_id": "S001_C001",
      "section_id": "S001",
      "section_title": None,
      "document_id": "doc-clause-001",
      "document_type": "txt",
      "text": "Legacy payload.",
      "span": {"start": 0, "end": 15},
      "clause_number": None,
    },
  )

  assert clause.clause_text == "Legacy payload."
  assert clause.text == "Legacy payload."


def test_sentence_splitter_preserves_compound_legal_statement() -> None:
  text = (
    "The Partner shall indemnify COMPANY and shall defend COMPANY "
    "against all claims arising under 42 U.S.C. \u00a7 1983."
  )
  units = SentenceSplitter().split(text)

  assert len(units) == 1
  assert units[0].text == text


def test_extractor_handles_empty_candidates(
  clause_extractor: ClauseExtractor,
) -> None:
  candidate_doc = _make_candidate_doc([])

  segmented = clause_extractor.process(candidate_doc)

  assert len(segmented.clauses) == 0


def test_extractor_preserves_candidate_order(
  clause_extractor: ClauseExtractor,
) -> None:
  candidates = [
    _make_candidate("Beta clause.", candidate_id="S001_P002", section_id="S001",
                     order=1),
    _make_candidate("Alpha clause.", candidate_id="S001_P001", section_id="S001",
                     order=0),
  ]
  candidate_doc = _make_candidate_doc(candidates)

  segmented = clause_extractor.process(candidate_doc)

  # Clauses should respect candidate order
  assert segmented.clauses[0].clause_text == "Beta clause."
  assert segmented.clauses[1].clause_text == "Alpha clause."
