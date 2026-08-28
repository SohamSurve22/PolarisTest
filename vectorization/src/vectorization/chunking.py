"""Skip short clauses and split long ones before embedding."""

from __future__ import annotations

import re
from collections.abc import Iterable

from document_pipeline.models.clause import Clause
from vectorization.models import EmbeddableRecord, clause_to_embeddable
from vectorization.sources import EmbeddableSource, decorate_retrieval_text

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def token_count(text: str) -> int:
  """Return the whitespace-separated token count of ``text``."""
  return len(text.split())


def split_text(text: str, *, max_tokens: int, overlap_tokens: int) -> list[str]:
  """Split ``text`` into chunks of at most ``max_tokens``.

  Prefers sentence boundaries. Adjacent chunks overlap by ``overlap_tokens``.
  A single sentence longer than ``max_tokens`` is hard-split by tokens.
  """
  stripped = text.strip()
  if not stripped:
    return []
  if token_count(stripped) <= max_tokens:
    return [stripped]

  pieces: list[str] = []
  for sentence in _SENTENCE_SPLIT.split(stripped):
    sentence = sentence.strip()
    if not sentence:
      continue
    if token_count(sentence) > max_tokens:
      pieces.extend(_token_windows(sentence.split(), max_tokens, overlap_tokens))
    else:
      pieces.append(sentence)

  chunks: list[str] = []
  current: list[str] = []
  current_tokens = 0

  def flush() -> None:
    nonlocal current, current_tokens
    if not current:
      return
    chunks.append(" ".join(current))
    current = []
    current_tokens = 0

  for piece in pieces:
    piece_tokens = piece.split()
    n = len(piece_tokens)
    if current and current_tokens + n > max_tokens:
      flush()
      if chunks and overlap_tokens > 0:
        overlap = chunks[-1].split()[-overlap_tokens:]
        room = max_tokens - n
        if room <= 0:
          overlap = []
        elif len(overlap) > room:
          overlap = overlap[-room:]
        current = list(overlap)
        current_tokens = len(current)
    current.extend(piece_tokens)
    current_tokens += n
  flush()
  return chunks


def clauses_to_embeddable(
  clauses: Iterable[Clause],
  *,
  min_tokens: int = 5,
  max_tokens: int = 512,
  overlap_tokens: int = 50,
) -> list[EmbeddableRecord]:
  """Skip short clauses and emit one EmbeddableRecord per chunk."""
  return sources_to_embeddable(
    [EmbeddableSource(clause=clause) for clause in clauses],
    min_tokens=min_tokens,
    max_tokens=max_tokens,
    overlap_tokens=overlap_tokens,
  )


def sources_to_embeddable(
  sources: Iterable[EmbeddableSource],
  *,
  min_tokens: int = 5,
  max_tokens: int = 512,
  overlap_tokens: int = 50,
) -> list[EmbeddableRecord]:
  """Skip/split sources, then append role/entity tags to retrieval_text."""
  records: list[EmbeddableRecord] = []
  for source in sources:
    if token_count(source.clause.clause_text) < min_tokens:
      continue
    chunks = split_text(
      source.clause.clause_text,
      max_tokens=max_tokens,
      overlap_tokens=overlap_tokens,
    )
    for index, chunk in enumerate(chunks):
      record = clause_to_embeddable(
        source.clause,
        chunk_text=chunk,
        chunk_index=index,
      )
      record.retrieval_text = decorate_retrieval_text(
        record.retrieval_text,
        role=source.role,
        entity_types=source.entity_types,
      )
      records.append(record)
  return records


def _token_windows(
  tokens: list[str],
  max_tokens: int,
  overlap_tokens: int,
) -> list[str]:
  if not tokens:
    return []
  windows: list[str] = []
  start = 0
  while start < len(tokens):
    end = min(start + max_tokens, len(tokens))
    windows.append(" ".join(tokens[start:end]))
    if end >= len(tokens):
      break
    next_start = end - overlap_tokens
    start = end if next_start <= start else next_start
  return windows
