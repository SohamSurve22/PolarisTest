"""CLI entry point for the Semantic Graph pipeline.

Usage:
    semantic-graph export <path> [--uri <uri>] [--user <user>] [--password <password>]
    semantic-graph export --text "<content>" [--uri <uri>] [--user <user>] [--password <password>]
"""

from __future__ import annotations

import argparse
import sys

from semantic_graph.cli.export_graph import register_export_command

_DESCRIPTION = "PolarisLex Semantic Graph — document ingestion & Neo4j export"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="semantic-graph",
        description=_DESCRIPTION,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command")
    register_export_command(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    return int(handler(args))


if __name__ == "__main__":
    sys.exit(main())
