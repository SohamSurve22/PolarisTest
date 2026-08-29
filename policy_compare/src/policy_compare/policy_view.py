"""Condensed policy view graph: document → sections (clauses in extra)."""

from __future__ import annotations

from collections import defaultdict

from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.section import SectionedDocument

from policy_compare.models import ViewEdge, ViewGraph, ViewNode

_INTRO_TITLE = "Introduction"


def _clause_of(entity_clause: object) -> object:
  contextual = entity_clause.contextual_clause  # type: ignore[attr-defined]
  return contextual.classified_clause.clause


def policy_view_graph(
  document: EntityDocument,
  sectioned: SectionedDocument | None = None,
) -> ViewGraph:
  """Turn an EntityDocument into a small document→section graph."""
  doc_id = document.metadata.document_id
  doc_title = document.metadata.title or document.metadata.filename or doc_id
  parents = {
    section.section_id: section.parent_section_id or ""
    for section in (sectioned.sections if sectioned is not None else [])
  }

  nodes: list[ViewNode] = [
    ViewNode(id=f"doc:{doc_id}", kind="document", title=doc_title),
  ]
  edges: list[ViewEdge] = []

  by_section: dict[str, list[object]] = defaultdict(list)
  for entity_clause in document.entity_clauses:
    clause = _clause_of(entity_clause)
    by_section[str(clause.section_id)].append(clause)  # type: ignore[attr-defined]

  for section_id, clauses in by_section.items():
    first = clauses[0]
    raw_title = getattr(first, "section_title", None)
    title = raw_title.strip() if isinstance(raw_title, str) and raw_title.strip() else _INTRO_TITLE
    texts = [str(getattr(c, "clause_text", "")).strip() for c in clauses]
    summary = " ".join(text for text in texts if text)
    node_id = f"section:{section_id}"
    parent_id = parents.get(section_id, "")
    extra = {
      "section_id": section_id,
      "clause_count": str(len(clauses)),
      "parent_section_id": parent_id,
    }
    nodes.append(
      ViewNode(
        id=node_id,
        kind="section",
        title=title,
        summary=summary,
        extra=extra,
      )
    )
    edges.append(ViewEdge(source=f"doc:{doc_id}", target=node_id, type="CONTAINS"))

  return ViewGraph(nodes=nodes, edges=edges)
