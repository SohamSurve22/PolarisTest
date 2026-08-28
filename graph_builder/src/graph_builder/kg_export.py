"""Dump GraphIR Obligation/Section nodes to vectorization kg_export JSON.

Does not open Neo4j and does not import vectorization. The JSON shape is the
contract in Spec 6 (law_code, sections, obligations).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from graph_builder.graph_ir import GraphIR, GraphNode

_OBLIGATION_SLOTS = ("subject", "action", "object", "condition", "exception")
_SECTION_REL_TYPES = frozenset({"IMPOSES", "HAS_OBLIGATION"})


def graph_ir_to_kg_dict(
  graph_ir: GraphIR,
  *,
  law_code: str | None = None,
  language: str = "en",
) -> dict[str, Any]:
  """Map GraphIR nodes into one kg_export file payload."""
  resolved_law = (law_code or "").strip() or _law_code_from_ir(graph_ir)
  if not resolved_law:
    raise ValueError("law_code is required (pass law_code= or add a LawVersion node)")

  section_id_by_node = _section_ids(graph_ir)
  sections = [_section_item(node, section_id_by_node[node.id]) for node in graph_ir.nodes if node.label == "Section"]
  obligations = [
    _obligation_item(node, graph_ir, section_id_by_node)
    for node in graph_ir.nodes
    if node.label == "Obligation"
  ]
  return {
    "law_code": resolved_law,
    "language": language,
    "sections": [item for item in sections if item is not None],
    "obligations": [item for item in obligations if item is not None],
  }


def write_kg_export(
  graph_ir: GraphIR,
  path: Path,
  *,
  law_code: str | None = None,
  language: str = "en",
) -> Path:
  """Write a kg_export JSON file. Creates parent directories if needed."""
  payload = graph_ir_to_kg_dict(graph_ir, law_code=law_code, language=language)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  return path


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
    prog="graph-builder-export-kg",
    description="Convert a GraphIR JSON file into vectorization kg_export JSON.",
  )
  parser.add_argument("ir_path", type=Path, help="Path to GraphIR JSON (nodes + relationships)")
  parser.add_argument(
    "-o",
    "--output",
    type=Path,
    required=True,
    help="Output JSON path (e.g. ../kg_export/DPDPA-2023.json)",
  )
  parser.add_argument("--law-code", default=None, help="Override law_code (else LawVersion properties)")
  parser.add_argument("--language", default="en")
  args = parser.parse_args(argv)

  graph_ir = GraphIR.from_json(args.ir_path.read_text(encoding="utf-8"))
  write_kg_export(graph_ir, args.output, law_code=args.law_code, language=args.language)
  return 0


def _law_code_from_ir(graph_ir: GraphIR) -> str:
  for node in graph_ir.nodes:
    if node.label != "LawVersion":
      continue
    for key in ("code", "law_code", "name"):
      value = _str_prop(node.properties, key)
      if value:
        return value
  return ""


def _section_ids(graph_ir: GraphIR) -> dict[str, str]:
  mapping: dict[str, str] = {}
  for node in graph_ir.nodes:
    if node.label != "Section":
      continue
    mapping[node.id] = (
      _str_prop(node.properties, "section_id")
      or _str_prop(node.properties, "number")
      or node.id
    )
  return mapping


def _section_item(node: GraphNode, section_id: str) -> dict[str, Any] | None:
  title = _str_prop(node.properties, "title") or _str_prop(node.properties, "name")
  body = _str_prop(node.properties, "text") or _str_prop(node.properties, "body")
  if title and body and body != title:
    text = f"{title}\n\n{body}"
  else:
    text = body or title
  if not text:
    return None
  return {"section_id": section_id, "title": title or None, "text": text}


def _obligation_item(
  node: GraphNode,
  graph_ir: GraphIR,
  section_id_by_node: dict[str, str],
) -> dict[str, Any] | None:
  text = _obligation_text(node.properties)
  if not text:
    return None
  section_id = _str_prop(node.properties, "section_id") or _section_id_from_rels(
    node.id, graph_ir, section_id_by_node
  )
  return {
    "obligation_id": node.id,
    "section_id": section_id or None,
    "text": text,
  }


def _obligation_text(properties: dict[str, Any]) -> str:
  explicit = _str_prop(properties, "text")
  if explicit:
    return explicit
  parts = [_str_prop(properties, key) for key in _OBLIGATION_SLOTS]
  return " ".join(part for part in parts if part)


def _section_id_from_rels(
  obligation_id: str,
  graph_ir: GraphIR,
  section_id_by_node: dict[str, str],
) -> str:
  for rel in graph_ir.relationships:
    if rel.type not in _SECTION_REL_TYPES:
      continue
    if rel.target == obligation_id and rel.source in section_id_by_node:
      return section_id_by_node[rel.source]
    if rel.source == obligation_id and rel.target in section_id_by_node:
      return section_id_by_node[rel.target]
  return ""


def _str_prop(properties: dict[str, Any], key: str) -> str:
  value = properties.get(key)
  if value is None:
    return ""
  text = str(value).strip()
  return text


if __name__ == "__main__":
  raise SystemExit(main())
