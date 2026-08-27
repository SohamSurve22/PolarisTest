"""Command-line entry point for the vectorization package."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from vectorization.config import get_settings
from vectorization.pipeline import run, search_text


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(prog="vectorization")
  subparsers = parser.add_subparsers(dest="command")

  search_parser = subparsers.add_parser("search", help="kNN search over ingested clauses")
  search_parser.add_argument("query", help="Query text to embed and search")
  search_parser.add_argument("--top-k", type=int, default=None)
  search_parser.add_argument("--min-score", type=float, default=None)
  search_parser.add_argument("--document-id", default=None)
  search_parser.add_argument("--source-type", default="document_clause")

  args = parser.parse_args(argv)
  settings = get_settings()
  logging.basicConfig(level=settings.log_level)

  if args.command == "search":
    hits = search_text(
      args.query,
      settings,
      top_k=args.top_k,
      min_score=args.min_score,
      source_type=args.source_type,
      document_id=args.document_id,
    )
    for hit in hits:
      sys.stdout.write(
        json.dumps(
          {
            "score": hit.score,
            "clause_id": hit.clause_id,
            "retrieval_text": hit.retrieval_text,
          }
        )
        + "\n"
      )
    return 0

  run(settings)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
