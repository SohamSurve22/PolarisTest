"""Stage 5: Document Understanding — structural clause classification.

The :func:`heuristic_classify` function returns a :class:`ClassificationResult`
containing the role, a confidence score, and a list of human-readable reason
labels.  A future transformer classifier would implement the same
:data:`ClassifierFn` contract, returning the same model — downstream stages
(``ClassifiedDocument``, Context Builder) require no changes.

``confidence`` is set to ``1.0`` for deterministic heuristic rules.  A
transformer classifier would provide calibrated scores.

``classification_reason`` provides explainability for each decision.
"""

import re
from collections.abc import Callable

from document_pipeline.core.base import BaseProcessor
from document_pipeline.models.clause import Clause, SegmentedDocument
from document_pipeline.models.semantic import (
  ClassificationResult,
  ClassifiedClause,
  ClassifiedDocument,
  StructuralRole,
)

_BULLET_RE = re.compile(r"^\s*[•\-*–]\s")
_NUMBERED_RE = re.compile(r"^\s*\d+[\.\)]\s")
_LETTERED_RE = re.compile(r"^\s*\(?[a-z]\)\s")

_COMMON_VERBS: frozenset[str] = frozenset({
  "shall", "will", "must", "may", "can", "should", "would", "could",
  "is", "are", "was", "were", "be", "been", "being", "am",
  "have", "has", "had", "do", "does", "did",
  "agree", "accept", "acknowledge", "represent", "warrant",
  "indemnify", "comply", "maintain", "provide", "ensure",
  "notify", "disclose", "process", "collect", "use", "share",
  "transfer", "store", "delete", "retain", "require", "prohibit",
  "permit", "authorize", "consent", "certify",
})


def _contains_verb(text: str) -> bool:
  words = {w.strip(".,;:!?()[]{}'\"") for w in text.lower().split()}
  return bool(words & _COMMON_VERBS)


def _is_list_item(text: str) -> bool:
  return bool(_BULLET_RE.match(text) or _NUMBERED_RE.match(text) or _LETTERED_RE.match(text))


def _is_heading(text: str, section_title: str | None) -> bool:
  words = text.split()
  if len(words) > 4:
    return False
  if section_title and (
    text.lower() == section_title.lower()
    or section_title.lower() in text.lower()
  ):
    return True
  if text[0].isupper() and not _contains_verb(text):
    return True
  return False


def heuristic_classify(clause: Clause) -> ClassificationResult:
  """Classify a clause's structural role using lightweight heuristics."""
  text = clause.clause_text.strip()
  if not text:
    return ClassificationResult(
      role=StructuralRole.UNKNOWN,
      classification_reason=["empty_text"],
    )

  if _is_list_item(text):
    return ClassificationResult(
      role=StructuralRole.LIST_ITEM,
      classification_reason=["list_marker_detected"],
    )

  if _is_heading(text, clause.section_title):
    reasons: list[str] = ["short_text"]
    if clause.section_title and (
      text.lower() == clause.section_title.lower()
      or clause.section_title.lower() in text.lower()
    ):
      reasons.append("matches_section_title")
    if text[0].isupper():
      reasons.append("title_case")
    if not _contains_verb(text):
      reasons.append("no_verb")
    return ClassificationResult(
      role=StructuralRole.HEADING,
      confidence=0.95 if "matches_section_title" in reasons else 0.85,
      classification_reason=reasons,
    )

  if _contains_verb(text):
    return ClassificationResult(
      role=StructuralRole.STATEMENT,
      confidence=0.92,
      classification_reason=["contains_verb"],
    )

  if len(text.split()) > 4:
    return ClassificationResult(
      role=StructuralRole.STATEMENT,
      confidence=0.65,
      classification_reason=["long_text"],
    )

  return ClassificationResult(
    role=StructuralRole.UNKNOWN,
    confidence=0.5,
    classification_reason=["no_heuristic_match"],
  )


ClassifierFn = Callable[[Clause], ClassificationResult]


class DocumentUnderstanding(BaseProcessor[SegmentedDocument, ClassifiedDocument]):
  """Classifies every clause into a structural role.

  Uses deterministic heuristics by default.  Swap the classifier for a
  transformer model by passing a :data:`ClassifierFn` that returns a
  :class:`ClassificationResult` — downstream code stays untouched.

  ``confidence`` enables downstream stages to threshold or filter uncertain
  predictions.  ``classification_reason`` aids debugging and evaluation.
  """

  def __init__(self, classifier: ClassifierFn = heuristic_classify) -> None:
    self._classifier = classifier

  def process(self, input_data: SegmentedDocument) -> ClassifiedDocument:
    classified = []
    for clause in input_data.clauses:
      result = self._classifier(clause)
      classified.append(
        ClassifiedClause(
          clause=clause,
          role=result.role,
          confidence=result.confidence,
          classification_reason=result.classification_reason,
        ),
      )
    return ClassifiedDocument(metadata=input_data.metadata, clauses=classified)
