"""Recall@k and latency bench for dense vs GraphRAG. Does not score policies."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rag.models import RagAnswer, RagCitation, RagError
from rag.service import answer_question

GOLD_PATH = Path(__file__).resolve().parents[2] / "tests" / "benchmark" / "gold_rag.json"

AnswerFn = Callable[..., RagAnswer]


@dataclass
class BenchRow:
  mode: str
  n_questions: int
  hits: int
  recall: float
  retrieve_ms: float
  generate_ms: float
  k: int

  def format(self) -> str:
    return (
      f"{self.mode:6}  recall@{self.k}={self.recall:.2f}  "
      f"hits={self.hits}/{self.n_questions}  "
      f"retrieve_ms={self.retrieve_ms:.1f}  generate_ms={self.generate_ms:.1f}"
    )


def load_gold(path: Path | None = None) -> dict:
  gold_path = path or GOLD_PATH
  return json.loads(gold_path.read_text(encoding="utf-8"))


def recall_hit(citations: list[RagCitation], gold_ids: list[str]) -> bool:
  cited = {row.id for row in citations}
  return any(gid in cited for gid in gold_ids)


def run_bench(
  *,
  answer: AnswerFn | None = None,
  gold_path: Path | None = None,
  modes: tuple[str, ...] = ("dense", "graph"),
) -> list[BenchRow]:
  gold = load_gold(gold_path)
  questions = gold["questions"]
  k = int(gold.get("k") or 5)
  answer_fn = answer or answer_question
  rows: list[BenchRow] = []
  for mode in modes:
    hits = 0
    retrieve_total = 0.0
    generate_total = 0.0
    for item in questions:
      result = answer_fn(item["question"], mode=mode)
      gold_ids = item["gold_dense_ids"] if mode == "dense" else item["gold_graph_ids"]
      if recall_hit(result.citations, gold_ids):
        hits += 1
      retrieve_total += result.retrieve_ms
      generate_total += result.generate_ms
    n = len(questions)
    rows.append(
      BenchRow(
        mode=mode,
        n_questions=n,
        hits=hits,
        recall=hits / n if n else 0.0,
        retrieve_ms=retrieve_total / n if n else 0.0,
        generate_ms=generate_total / n if n else 0.0,
        k=k,
      )
    )
  return rows


def format_table(rows: list[BenchRow]) -> str:
  header = "mode    recall@k           hits           retrieve_ms  generate_ms"
  return "\n".join([header, *[row.format() for row in rows]])


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(prog="rag-bench")
  parser.add_argument("--gold", type=Path, default=None)
  args = parser.parse_args(argv)
  try:
    rows = run_bench(gold_path=args.gold)
  except RagError as exc:
    sys.stderr.write(f"rag-bench skipped: {exc}\n")
    return 2
  sys.stdout.write(format_table(rows) + "\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
