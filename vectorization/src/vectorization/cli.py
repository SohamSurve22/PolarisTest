"""Command-line entry point for the vectorization package."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from vectorization.config import get_settings
from vectorization.pipeline import reembed, run, run_kg, run_rag, search_text


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(prog="vectorization")
  subparsers = parser.add_subparsers(dest="command")

  search_parser = subparsers.add_parser("search", help="kNN search over ingested clauses")
  search_parser.add_argument("query", help="Query text to embed and search")
  search_parser.add_argument("--top-k", type=int, default=None)
  search_parser.add_argument("--min-score", type=float, default=None)
  search_parser.add_argument("--document-id", default=None)
  search_parser.add_argument("--source-type", default="document_clause")
  subparsers.add_parser(
    "ingest-kg",
    help="ingest KG obligation and section JSON into Qdrant",
  )
  ingest_rag = subparsers.add_parser(
    "ingest-rag",
    help="ingest merged statute JSON as rag_section (not kg_obligation)",
  )
  ingest_rag.add_argument(
    "--path",
    default=None,
    help="merged JSON path (default VECTORIZATION_RAG_PATH)",
  )
  subparsers.add_parser(
    "reembed",
    help="re-embed KG then document clauses under the current model",
  )

  args = parser.parse_args(argv)
  settings = get_settings()
  logging.basicConfig(level=settings.log_level)

  if args.command == "reembed":
    reembed(settings)
    return 0

  if args.command == "ingest-kg":
    run_kg(settings)
    return 0

  if args.command == "ingest-rag":
    run_rag(settings, path=Path(args.path) if args.path else None)
    return 0

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
