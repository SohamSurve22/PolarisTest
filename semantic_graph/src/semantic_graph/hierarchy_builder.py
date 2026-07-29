"""Hierarchy builder — constructs the document skeleton from an EntityDocument.

This is the first stage of the Semantic Graph Builder pipeline.  It converts
the flat clause list in an ``EntityDocument`` into a hierarchical ``GraphIR``
with ``LawVersion → Chapter → Section → SubSection → Clause`` structure.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

if TYPE_CHECKING:
    from document_pipeline.models.entity import EntityDocument

_LAWVERSION = "LawVersion"
_CHAPTER = "Chapter"
_SECTION = "Section"
_SUBSECTION = "SubSection"
_CLAUSE = "Clause"

_LEVEL: dict[str, int] = {
    _LAWVERSION: 0,
    _CHAPTER: 1,
    _SECTION: 2,
    _SUBSECTION: 3,
    _CLAUSE: 4,
}

_REL_TYPE: dict[tuple[str, str], str] = {
    (_LAWVERSION, _CHAPTER): "HAS_CHAPTER",
    (_LAWVERSION, _SECTION): "HAS_SECTION",
    (_LAWVERSION, _SUBSECTION): "HAS_SUBSECTION",
    (_LAWVERSION, _CLAUSE): "HAS_CLAUSE",
    (_CHAPTER, _SECTION): "HAS_SECTION",
    (_CHAPTER, _SUBSECTION): "HAS_SUBSECTION",
    (_CHAPTER, _CLAUSE): "HAS_CLAUSE",
    (_SECTION, _SUBSECTION): "HAS_SUBSECTION",
    (_SECTION, _CLAUSE): "HAS_CLAUSE",
    (_SUBSECTION, _CLAUSE): "HAS_CLAUSE",
}

_CHAPTER_PREFIXES = frozenset({
    "chapter", "ch", "article", "schedule", "part", "title", "book",
})

_NUMBERED_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s")

_ROMAN_RE = re.compile(
    r"^"
    r"(M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))"
    r"\.?\s",
    re.IGNORECASE,
)


class HierarchyBuilder:
    """Builds a hierarchical ``GraphIR`` from an ``EntityDocument``.

    The builder traverses the document's clauses in document order, detects
    hierarchy transitions (Chapter, Section, SubSection), and creates
    ``GraphNode`` and ``GraphRelationship`` objects while preserving order
    and preventing duplicates.

    No LLM or Neo4j code is used.
    """

    def build(self, document: EntityDocument) -> GraphIR:
        """Convert an ``EntityDocument`` into a hierarchical ``GraphIR``.

        Args:
            document: The entity-annotated document to build a hierarchy for.

        Returns:
            A ``GraphIR`` containing hierarchy nodes and relationships.

        Raises:
            ValueError: If the document contains no clauses.
        """
        if not document.entity_clauses:
            raise ValueError("Cannot build hierarchy for an empty document.")

        graph = GraphIR(nodes=[], relationships=[])
        seen_ids: set[str] = set()

        law_node = _make_law_node(document)
        _add_node(graph, law_node, seen_ids)
        stack: list[tuple[str, GraphNode]] = [(_LAWVERSION, law_node)]

        prev_section_id: str | None = None
        section_nodes: dict[str, GraphNode] = {}

        for entity_clause in document.entity_clauses:
            clause = entity_clause.contextual_clause.classified_clause.clause
            section_id = clause.section_id

            if section_id != prev_section_id:
                prev_section_id = section_id
                if section_id not in section_nodes:
                    h_node = _build_hierarchy_node(
                        clause.section_title, section_id,
                    )
                    section_nodes[section_id] = h_node
                    _add_node(graph, h_node, seen_ids)
                    _adjust_stack(stack, h_node, graph)

            clause_node = _make_clause_node(clause)
            _add_node(graph, clause_node, seen_ids)
            _connect_clause(stack, clause_node, graph)

        return graph


def _detect_node_type(title: str | None) -> str:
    """Determine the hierarchy node type from a section title."""
    if not title or not title.strip():
        return _SECTION

    stripped = title.strip()
    first_word = stripped.split()[0].lower().rstrip(".")

    if first_word in _CHAPTER_PREFIXES:
        return _CHAPTER

    numbered = _NUMBERED_RE.match(stripped)
    if numbered:
        return _SUBSECTION if "." in numbered.group(1) else _SECTION

    if _ROMAN_RE.match(stripped):
        return _SECTION

    return _SECTION


def _extract_number(title: str | None) -> str:
    """Extract numbering prefix from a title (e.g. '1' from 'CHAPTER 1: Intro')."""
    if not title:
        return ""
    stripped = title.strip()
    numbered = _NUMBERED_RE.match(stripped)
    if numbered:
        return numbered.group(1)
    # Handle "CHAPTER 1: Intro", "Article 5: Title", etc.
    word_num = re.match(
        r"^(?:chapter|ch\.?|article|schedule|part|title|book)\s+(\d+|[IVXLCDM]+)",
        stripped,
        re.IGNORECASE,
    )
    return word_num.group(1) if word_num else ""


def _make_law_node(document: EntityDocument) -> GraphNode:
    """Create the ``LawVersion`` root node from document metadata."""
    md = document.metadata
    return GraphNode(
        id=f"law_{md.document_id}",
        label=_LAWVERSION,
        properties={
            "law_code": md.document_id,
            "title": md.title or "",
        },
        source_clause=None,
    )


def _build_hierarchy_node(
    section_title: str | None,
    section_id: str,
) -> GraphNode:
    """Create a Chapter, Section, or SubSection node from section metadata."""
    node_type = _detect_node_type(section_title)

    if node_type == _CHAPTER:
        num = _extract_number(section_title)
        return GraphNode(
            id=f"chapter_{section_id}",
            label=_CHAPTER,
            properties={
                "number": num,
                "title": section_title or "",
            },
            source_clause=None,
        )

    if node_type == _SUBSECTION:
        return GraphNode(
            id=f"subsection_{section_id}",
            label=_SUBSECTION,
            properties={
                "identifier": section_title or "",
            },
            source_clause=None,
        )

    num = _extract_number(section_title)
    return GraphNode(
        id=f"section_{section_id}",
        label=_SECTION,
        properties={
            "number": num,
            "title": section_title or "",
        },
        source_clause=None,
    )


def _make_clause_node(clause: object) -> GraphNode:
    """Create a ``Clause`` node from a clause model."""
    cid = getattr(clause, "clause_id", "")
    text = getattr(clause, "clause_text", getattr(clause, "text", ""))
    return GraphNode(
        id=f"clause_{cid}",
        label=_CLAUSE,
        properties={
            "clause_id": cid,
            "text": text,
            "confidence": 1.0,
        },
        source_clause=text,
    )


def _adjust_stack(
    stack: list[tuple[str, GraphNode]],
    node: GraphNode,
    graph: GraphIR,
) -> None:
    """Pop the stack to find the correct parent and create the relationship."""
    node_level = _LEVEL[node.label]
    while stack and _LEVEL[stack[-1][0]] >= node_level:
        stack.pop()

    if stack:
        parent = stack[-1][1]
        rel_type = _REL_TYPE.get((parent.label, node.label), "HAS_SECTION")
        graph.relationships.append(
            GraphRelationship(source=parent.id, target=node.id, type=rel_type),
        )

    stack.append((node.label, node))


def _connect_clause(
    stack: list[tuple[str, GraphNode]],
    node: GraphNode,
    graph: GraphIR,
) -> None:
    """Connect a ``Clause`` node to its nearest valid parent."""
    if not stack:
        return
    parent = stack[-1][1]
    rel_type = _REL_TYPE.get((parent.label, node.label), "HAS_CLAUSE")
    graph.relationships.append(
        GraphRelationship(source=parent.id, target=node.id, type=rel_type),
    )


def _add_node(graph: GraphIR, node: GraphNode, seen_ids: set[str]) -> None:
    """Add a node, skipping if its ID already exists."""
    if node.id in seen_ids:
        return
    seen_ids.add(node.id)
    graph.nodes.append(node)
