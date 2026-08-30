"""CLI: lift tagged law JSON catalogs into GraphIR Obligation nodes."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from graph_builder.graph_ir import GraphIR

from semantic_graph.cli.export_graph import _push_neo4j


def register_from_catalog_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "from-catalog",
        help="Build GraphIR Obligation/Penalty nodes from tagged law JSON.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="One or more *_graph.json catalog files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output GraphIR JSON path.",
    )
    parser.add_argument(
        "--to-neo4j",
        action="store_true",
        help="Also MERGE the GraphIR into Neo4j.",
    )
    parser.add_argument(
        "--uri",
        default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j connection URI (default: bolt://localhost:7687, env: NEO4J_URI).",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("NEO4J_USER", "neo4j"),
        help="Neo4j username (default: neo4j, env: NEO4J_USER).",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("NEO4J_PASSWORD", ""),
        help="Neo4j password (env: NEO4J_PASSWORD).",
    )
    parser.set_defaults(handler=_handle_from_catalog)


def catalog_to_ir_from_paths(paths: list[Path]) -> GraphIR:
    from compliance.graph_scope import ir_from_paths

    return ir_from_paths(paths)


def _handle_from_catalog(args: argparse.Namespace) -> int:
    if not args.paths:
        print("error: provide at least one catalog JSON file.", file=sys.stderr)
        return 2
    try:
        for path in args.paths:
            resolved = path.expanduser().resolve()
            if not resolved.is_file():
                raise OSError(f"Catalog not found: {resolved}")
        graph = catalog_to_ir_from_paths(list(args.paths))
        written = graph.write_json(args.output)
        print(f"Wrote GraphIR: {written}", file=sys.stderr)
        print(
            f"Graph built: {len(graph.nodes)} nodes, {len(graph.relationships)} relationships",
            file=sys.stderr,
        )
        if args.to_neo4j:
            return _push_neo4j(graph, args.uri, args.user, args.password)
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
