"""CLI command: run document pipeline → build graph → export to Neo4j."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from document_pipeline.models.document import DocumentSource
from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.orchestrator import PipelineOutputs, create_default_orchestrator
from document_pipeline.utils.document_ids import generate_document_id
from graph_builder.graph_ir import GraphIR

from semantic_graph.neo4j_exporter import Neo4jExporter
from semantic_graph.semantic_graph_builder import SemanticGraphBuilder


def register_export_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``export`` subcommand on *subparsers*."""
    parser = subparsers.add_parser(
        "export",
        help="Ingest a document and export its semantic graph to Neo4j.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to a .txt, .pdf, or .docx document.",
    )
    parser.add_argument(
        "--text",
        help="Inline plain-text document content to process.",
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
    parser.set_defaults(handler=_handle_export)


def _handle_export(args: argparse.Namespace) -> int:
    if args.text and args.path:
        print("error: provide either a file path or --text, not both.", file=sys.stderr)
        return 2

    if not args.text and not args.path:
        print("error: provide a file path or --text.", file=sys.stderr)
        return 2

    try:
        if args.text is not None:
            return _export_from_text(args.text, args.uri, args.user, args.password)

        return _export_from_path(Path(args.path), args.uri, args.user, args.password)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Source helpers
# ---------------------------------------------------------------------------

_SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def _build_source(path: Path) -> DocumentSource:
    _validate_path(path)
    fmt = _format_from_extension(path.suffix)
    metadata = DocumentMetadata(
        document_id=generate_document_id(),
        filename=path.name,
        format=fmt,
        source_path=str(path),
    )
    return DocumentSource(metadata=metadata)


def _validate_path(path: Path) -> None:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        msg = f"Document not found: {resolved}"
        raise OSError(msg)
    if resolved.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        msg = f"Unsupported file type: {resolved.suffix.lower() or 'unknown'}"
        raise OSError(msg)


def _format_from_extension(extension: str) -> DocumentFormat:
    mapping = {
        ".pdf": DocumentFormat.PDF,
        ".docx": DocumentFormat.DOCX,
        ".txt": DocumentFormat.TXT,
    }
    return mapping.get(extension.lower(), DocumentFormat.UNKNOWN)


# ---------------------------------------------------------------------------
# Export flows
# ---------------------------------------------------------------------------


def _export_from_path(path: Path, uri: str, user: str, password: str) -> int:
    source = _build_source(path)
    return _export(source, uri, user, password)


def _export_from_text(text: str, uri: str, user: str, password: str) -> int:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
    ) as handle:
        handle.write(text)
        temp_path = Path(handle.name)

    try:
        source = _build_source(temp_path)
        return _export(source, uri, user, password)
    finally:
        temp_path.unlink(missing_ok=True)


def _export(source: DocumentSource, uri: str, user: str, password: str) -> int:
    doc_id = source.metadata.document_id
    print(f"Processing document: {doc_id}", file=sys.stderr)

    outputs = _run_document_pipeline(source)

    print("Building semantic graph…", file=sys.stderr)

    graph = _build_semantic_graph(outputs.entity)

    print(
        f"Graph built: {len(graph.nodes)} nodes, {len(graph.relationships)} relationships",
        file=sys.stderr,
    )

    print(f"Connecting to Neo4j at {uri}…", file=sys.stderr)

    stats = _export_to_neo4j(graph, uri, user, password)

    print(
        f"Export complete: {stats['nodes_created']} nodes, "
        f"{stats['relationships_created']} relationships created",
        file=sys.stderr,
    )

    return 0


def _run_document_pipeline(
    source: DocumentSource,
) -> PipelineOutputs:
    orchestrator = create_default_orchestrator()
    return orchestrator.run(source)


def _build_semantic_graph(entity_document: EntityDocument) -> GraphIR:
    builder = SemanticGraphBuilder()
    return builder.build(entity_document)


def _export_to_neo4j(graph: GraphIR, uri: str, user: str, password: str) -> dict[str, int]:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        exporter = Neo4jExporter(driver=driver)
        return exporter.export(graph)
    finally:
        driver.close()
