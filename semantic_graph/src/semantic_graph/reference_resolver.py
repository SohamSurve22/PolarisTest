"""Reference resolver — discovers cross-references and connects graph nodes.

This stage runs after the hierarchy builder.  It traverses every clause in
the ``EntityDocument``, detects references (Section 43A, Rule 5, Chapter IX,
etc.) using parser metadata when available, resolves them against existing
hierarchy nodes, and creates ``REFERENCES`` or ``UNRESOLVED_REFERENCE``
relationships.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from semantic_graph.semantic_graph_stage import SemanticGraphStage

if TYPE_CHECKING:
    from document_pipeline.models.entity import EntityDocument

_REFERENCE_TYPE = "REFERENCES"
_UNRESOLVED_TYPE = "UNRESOLVED_REFERENCE"
_UNRESOLVED_LABEL = "UnresolvedReference"

# Fallback patterns for reference types NOT covered by the parser's
# ReferenceDetector (which handles section, subsection, rule, article,
# chapter, schedule, clause numeric, regulation, act, rules, code).
_FALLBACK_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("part", re.compile(r"(?i)\bpart\s+([IVXLCDM]+|\d+)"), "part"),
    ("clause_lettered", re.compile(r"(?i)\bclause\s+\(([a-z])\)"), "clause"),
    ("explanation", re.compile(r"(?i)\bExplanation\b"), "explanation"),
    ("proviso", re.compile(r"(?i)\bProviso\b"), "proviso"),
]


class ReferenceResolver(SemanticGraphStage):
    """Detects and resolves cross-references inside legal document clauses.

    Uses the parser-provided ``detected_references`` on each
    ``ContextualClause`` as the primary data source, supplemented by
    fallback regex patterns for reference types not covered by the parser.

    Resolution matches references against existing hierarchy nodes
    (Chapter, Section, SubSection, Clause).  Unmatched references
    produce ``UnresolvedReference`` nodes.
    """

    def __init__(self) -> None:
        self._seen_relationships: set[tuple[str, str, str]] = set()
        self._seen_unresolved: set[str] = set()

    def process(
        self,
        document: EntityDocument,
        graph: GraphIR,
    ) -> GraphIR:
        """Resolve cross-references in every clause.

        Args:
            document: The original entity-annotated document.
            graph: The ``GraphIR`` produced by ``HierarchyBuilder``.

        Returns:
            A new ``GraphIR`` with reference relationships added.
        """
        if not document.entity_clauses:
            return graph

        self._seen_relationships.clear()
        self._seen_unresolved.clear()

        index = _build_node_index(graph)
        clause_node_map = _build_clause_node_map(graph)

        result = GraphIR(
            nodes=list(graph.nodes),
            relationships=list(graph.relationships),
        )

        for entity_clause in document.entity_clauses:
            ctx = entity_clause.contextual_clause
            clause = ctx.classified_clause.clause
            clause_id = clause.clause_id
            clause_node_id = clause_node_map.get(clause_id)
            if clause_node_id is None:
                continue

            refs = self._collect_references(ctx, clause, clause_id)
            for ref_type, ref_value, ref_text, _span_start in refs:
                self._process_reference(
                    result, clause_node_id, clause_id,
                    ref_type, ref_value, ref_text, index,
                )

        return result

    def _collect_references(
        self,
        ctx: object,
        clause: object,
        clause_id: str,
    ) -> list[tuple[str, str, str, int]]:
        """Collect references from parser metadata and fallback patterns.

        Returns list of (ref_type, ref_value, ref_text, span_start).
        """
        collected: list[tuple[str, str, str, int]] = []
        seen_spans: set[tuple[int, int]] = set()

        parser_refs = self._parser_references(ctx)
        for ref_type, ref_value, ref_text, start, end in parser_refs:
            span = (start, end)
            if span not in seen_spans:
                seen_spans.add(span)
                collected.append((ref_type, ref_value, ref_text, start))

        clause_text = _get_clause_text(clause)
        fallback_refs = self._fallback_references(clause_text)
        for ref_type, ref_value, ref_text, start, end in fallback_refs:
            span = (start, end)
            if span not in seen_spans:
                seen_spans.add(span)
                collected.append((ref_type, ref_value, ref_text, start))

        collected.sort(key=lambda x: x[3])
        return collected

    @staticmethod
    def _parser_references(
        ctx: object,
    ) -> list[tuple[str, str, str, int, int]]:
        """Extract references from parser metadata (detected_references)."""
        results: list[tuple[str, str, str, int, int]] = []
        refs = _get_detected_references(ctx)
        for ref in refs:
            ref_text = _get_ref_text(ref)
            ref_type = _get_ref_type(ref)
            start = _get_ref_start(ref)
            end = _get_ref_end(ref)
            if not ref_text or not ref_type:
                continue
            value = _extract_reference_value(ref_type, ref_text)
            mapped_type = _map_reference_type(ref_type)
            results.append((mapped_type, value, ref_text, start, end))
        return results

    @staticmethod
    def _fallback_references(
        text: str,
    ) -> list[tuple[str, str, str, int, int]]:
        """Detect references using fallback regex patterns."""
        results: list[tuple[str, str, str, int, int]] = []
        for ref_type, pattern, mapped_type in _FALLBACK_PATTERNS:
            for match in pattern.finditer(text):
                if ref_type == "explanation" or ref_type == "proviso":
                    value = match.group(0)
                elif ref_type == "clause_lettered":
                    value = match.group(1)
                else:
                    value = match.group(1)
                span_start = match.start()
                span_end = match.end()
                results.append((
                    mapped_type, value, match.group(0), span_start, span_end,
                ))
        return results

    def _process_reference(
        self,
        graph: GraphIR,
        source_node_id: str,
        source_clause_id: str,
        ref_type: str,
        ref_value: str,
        ref_text: str,
        index: dict[str, dict[str, str]],
    ) -> None:
        """Resolve a single reference and add the appropriate relationship."""
        target_id = _resolve(ref_type, ref_value, index)
        if target_id is not None:
            if target_id == source_node_id:
                return
            rel_key = (source_node_id, target_id, _REFERENCE_TYPE)
            if rel_key in self._seen_relationships:
                return
            self._seen_relationships.add(rel_key)
            graph.relationships.append(
                GraphRelationship(
                    source=source_node_id,
                    target=target_id,
                    type=_REFERENCE_TYPE,
                ),
            )
        else:
            unresolved_id = f"unresolved_{source_clause_id}_{ref_type}_{_normalize(ref_value)}"
            if unresolved_id not in self._seen_unresolved:
                self._seen_unresolved.add(unresolved_id)
                graph.nodes.append(
                    GraphNode(
                        id=unresolved_id,
                        label=_UNRESOLVED_LABEL,
                        properties={
                            "reference_text": ref_text,
                            "reference_type": ref_type,
                            "clause_id": source_clause_id,
                        },
                        source_clause=source_clause_id,
                    ),
                )
            rel_key = (source_node_id, unresolved_id, _UNRESOLVED_TYPE)
            if rel_key in self._seen_relationships:
                return
            self._seen_relationships.add(rel_key)
            graph.relationships.append(
                GraphRelationship(
                    source=source_node_id,
                    target=unresolved_id,
                    type=_UNRESOLVED_TYPE,
                ),
            )


def _build_node_index(graph: GraphIR) -> dict[str, dict[str, str]]:
    """Build lookup indices for hierarchy nodes.

    Returns a dict mapping reference-type names to dicts of
    ``{normalized_value: node_id}``.
    """
    idx: dict[str, dict[str, str]] = {
        "section": {},
        "chapter": {},
        "subsection": {},
        "clause": {},
        "law": {},
        "title_index": {},
    }

    for node in graph.nodes:
        label = node.label
        props = node.properties

        if label == "Section":
            num = props.get("number", "")
            if num:
                idx["section"][num.lower()] = node.id
        elif label == "Chapter":
            num = props.get("number", "")
            if num:
                idx["chapter"][num.lower()] = node.id
        elif label == "SubSection":
            ident = props.get("identifier", "")
            num = _extract_number_from_text(ident)
            if num:
                idx["subsection"][num.lower()] = node.id
            if ident:
                idx["subsection"][ident.lower()] = node.id
        elif label == "Clause":
            cnum = props.get("clause_number", "")
            if cnum:
                idx["clause"][cnum.lower()] = node.id
        elif label == "LawVersion":
            code = props.get("law_code", "")
            if code:
                idx["law"][code.lower()] = node.id

    for node in graph.nodes:
        title = node.properties.get("title", "")
        if title:
            idx["title_index"][title.lower()] = node.id

    return idx


def _build_clause_node_map(graph: GraphIR) -> dict[str, str]:
    """Map ``clause_id`` (e.g. ``S001_C001``) to its node ID."""
    mapping: dict[str, str] = {}
    for node in graph.nodes:
        if node.label == "Clause":
            cid = node.properties.get("clause_id", "")
            if cid:
                mapping[cid] = node.id
    return mapping


def _map_reference_type(parser_type: str) -> str:
    """Map a parser reference type to a canonical reference type."""
    mapping = {
        "section": "section",
        "subsection": "subsection",
        "rule": "rule",
        "article": "article",
        "chapter": "chapter",
        "schedule": "schedule",
        "clause": "clause",
        "regulation": "regulation",
        "act": "act",
        "rules": "rules",
        "code": "code",
    }
    return mapping.get(parser_type, parser_type)


def _extract_reference_value(ref_type: str, ref_text: str) -> str:
    """Extract the identifier value from a reference text.

    E.g. ``"43A"`` from ``"Section 43A"``, ``"IX"`` from ``"Chapter IX"``.
    """
    t = ref_type.lower()

    if t == "subsection":
        m = re.search(r"\((\d+|[a-z])\)", ref_text)
        return m.group(1) if m else ref_text
    if t in ("section", "clause", "rule", "article", "regulation"):
        m = re.search(r"(\d+[A-Z]?(?:-[A-Za-z])?)", ref_text)
        return m.group(1) if m else ref_text
    if t in ("chapter", "schedule", "part"):
        m = re.search(r"\b([IVXLCDM]+)\b", ref_text, re.IGNORECASE)
        return m.group(1).upper() if m else ref_text
    if t in ("act", "rules", "code"):
        return ref_text
    return ref_text


def _extract_number_from_text(text: str) -> str:
    """Extract the first number from a subsection identifier."""
    if not text:
        return ""
    m = re.search(r"\((\d+|[a-z])\)", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d+(?:\.\d+)*)", text)
    return m.group(1) if m else ""


def _resolve(
    ref_type: str,
    ref_value: str,
    index: dict[str, dict[str, str]],
) -> str | None:
    """Try to find an existing node matching the reference.

    Returns the node ID if found, ``None`` otherwise.
    """
    val = ref_value.lower()

    if ref_type == "section":
        return index["section"].get(val)
    if ref_type == "chapter":
        return index["chapter"].get(val)
    if ref_type == "subsection":
        result = index["subsection"].get(val)
        if result is not None:
            return result
        parenthetical = re.search(r"\((\d+|[a-z])\)", val)
        if parenthetical:
            return index["subsection"].get(parenthetical.group(1).lower())
        return None
    if ref_type == "article":
        return index["chapter"].get(val) or index["section"].get(val)
    if ref_type == "part":
        return index["chapter"].get(val) or index["section"].get(val)
    if ref_type == "clause":
        return index["clause"].get(val)
    if ref_type == "schedule":
        return None
    if ref_type == "rule":
        return None
    if ref_type == "regulation":
        return None
    if ref_type == "act":
        return index["law"].get(val)
    if ref_type == "explanation":
        return _find_by_title_contains(index, "explanation")
    if ref_type == "proviso":
        return _find_by_title_contains(index, "proviso")
    return None


def _find_by_title_contains(
    index: dict[str, dict[str, str]],
    keyword: str,
) -> str | None:
    """Find the first node whose title contains *keyword*."""
    for title_lower, node_id in index.get("title_index", {}).items():
        if keyword in title_lower:
            return node_id
    return None


def _normalize(value: str) -> str:
    """Normalize a value for use in node IDs."""
    return re.sub(r"[^a-zA-Z0-9]", "_", value).lower()


# ---------------------------------------------------------------------------
# Duck-typed accessors for parser models (avoid runtime imports)
# ---------------------------------------------------------------------------


def _get_clause_text(clause: object) -> str:
    return getattr(clause, "clause_text", getattr(clause, "text", ""))


def _get_detected_references(ctx: object) -> list[object]:
    return getattr(ctx, "detected_references", [])


def _get_ref_text(ref: object) -> str:
    return getattr(ref, "reference_text", "")


def _get_ref_type(ref: object) -> str:
    return getattr(ref, "reference_type", "")


def _get_ref_start(ref: object) -> int:
    return getattr(ref, "start", 0)


def _get_ref_end(ref: object) -> int:
    return getattr(ref, "end", 0)
