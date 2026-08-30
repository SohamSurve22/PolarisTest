"""Statute Q&A entry point. Does not score policies or write the memo."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from vectorization.models import SearchHit

from rag.generate import ChatFn, generate_answer
from rag.models import RagAnswer, RagError
from rag.retrieve import SearchFn, retrieve_dense, retrieve_graph

Mode = Literal["dense", "graph"]


def default_search(
  query: str,
  *,
  source_type: str,
  top_k: int,
  min_score: float | None = None,
) -> list[SearchHit]:
  from vectorization.pipeline import search_text

  try:
    return search_text(
      query,
      source_type=source_type,
      top_k=top_k,
      min_score=min_score if min_score is not None else 0.0,
    )
  except Exception as exc:
    raise RagError("Q&A search backend unavailable (Qdrant or Ollama).") from exc


def answer_question(
  question: str,
  mode: Mode = "dense",
  *,
  search: SearchFn | None = None,
  chat: ChatFn | None = None,
  ir=None,
  law_paths: list[Path] | None = None,
) -> RagAnswer:
  text = (question or "").strip()
  if not text:
    raise ValueError("question is required")
  if mode not in {"dense", "graph"}:
    raise ValueError(f"unsupported RAG mode: {mode}")

  search_fn: SearchFn = search or default_search
  started = time.perf_counter()
  if mode == "dense":
    citations = retrieve_dense(text, search=search_fn)
  else:
    citations = retrieve_graph(text, search=search_fn, ir=ir, law_paths=law_paths)
  retrieve_ms = (time.perf_counter() - started) * 1000.0

  gen_started = time.perf_counter()
  try:
    answer = generate_answer(text, citations, chat=chat)
  except RagError:
    raise
  except Exception as exc:
    raise RagError("Q&A chat backend unavailable (Ollama).") from exc
  generate_ms = (time.perf_counter() - gen_started) * 1000.0

  return RagAnswer(
    mode=mode,
    answer=answer,
    citations=citations,
    retrieve_ms=retrieve_ms,
    generate_ms=generate_ms,
  )
