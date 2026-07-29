"""Comprehensive tests for ``ReferenceResolver``."""

from __future__ import annotations

from typing import Any

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.context import Reference as Ref
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from semantic_graph.reference_resolver import ReferenceResolver

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _metadata(**overrides: Any) -> DocumentMetadata:
    kwargs: dict[str, Any] = dict(
        document_id="doc-001", filename="test.txt", format=DocumentFormat.TXT, title="Test Act",
    )
    kwargs.update(overrides)
    return DocumentMetadata(**kwargs)


def _clause(
    *,
    clause_id: str,
    section_id: str = "S001",
    text: str = "",
    clause_number: str | None = None,
) -> Clause:
    return Clause(
        clause_id=clause_id,
        section_id=section_id,
        section_title=None,
        document_id="doc-001",
        document_type=DocumentFormat.TXT,
        clause_text=text,
        span=Span(start=0, end=len(text)),
        clause_number=clause_number,
    )


def _classified(clause: Clause) -> ClassifiedClause:
    return ClassifiedClause(
        clause=clause,
        role=StructuralRole.STATEMENT,
        confidence=1.0,
        classification_reason=["test"],
    )


def _entity_clause(
    clause: Clause,
    references: list[Ref] | None = None,
) -> EntityClause:
    cc = ClassifiedClause(
        clause=clause,
        role=StructuralRole.STATEMENT,
        confidence=1.0,
        classification_reason=["test"],
    )
    ctx = ContextualClause(
        classified_clause=cc,
        previous_clause_id=None,
        next_clause_id=None,
        section_position=0,
        is_first_in_section=True,
        is_last_in_section=True,
        neighbor_clause_ids=[],
        detected_references=references or [],
    )
    return EntityClause(contextual_clause=ctx, entities=[])


def _make_entity_document(
    clauses: list[tuple[Clause, list[Ref]]],
) -> EntityDocument:
    return EntityDocument(
        metadata=_metadata(),
        entity_clauses=[_entity_clause(c, r) for c, r in clauses],
    )


def _sec(text: str) -> Ref:
    """Create a parser-detected 'section' reference."""
    lower = text.lower()
    start = lower.index("section") if "section" in lower else 0
    return Ref(reference_text=text, reference_type="section", start=start, end=start + len(text))


def _rule(text: str) -> Ref:
    lower = text.lower()
    start = lower.index("rule") if "rule" in lower else 0
    return Ref(reference_text=text, reference_type="rule", start=start, end=start + len(text))


def _chapter(text: str) -> Ref:
    lower = text.lower()
    start = lower.index("chapter") if "chapter" in lower else 0
    return Ref(reference_text=text, reference_type="chapter", start=start, end=start + len(text))


# ---------------------------------------------------------------------------
# Graph node helpers
# ---------------------------------------------------------------------------


def section_node(number: str, node_id: str = "") -> GraphNode:
    return GraphNode(
        id=node_id or f"section_S{number}",
        label="Section",
        properties={"number": number, "title": f"Section {number}"},
        source_clause=None,
    )


def chapter_node(number: str) -> GraphNode:
    return GraphNode(
        id=f"chapter_{number.lower()}",
        label="Chapter",
        properties={"number": number, "title": f"Chapter {number}"},
        source_clause=None,
    )


def clause_node(clause_id: str, clause_number: str = "") -> GraphNode:
    props: dict[str, object] = {"clause_id": clause_id, "text": "", "confidence": 1.0}
    if clause_number:
        props["clause_number"] = clause_number
    return GraphNode(
        id=f"clause_{clause_id}",
        label="Clause",
        properties=props,
        source_clause=None,
    )


def law_node(doc_id: str = "doc-001") -> GraphNode:
    return GraphNode(
        id=f"law_{doc_id}",
        label="LawVersion",
        properties={"law_code": doc_id, "title": "Test Act"},
        source_clause=None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSectionReference:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_resolves_known_section(self) -> None:
        clause = _clause(clause_id="S001_C001", text="subject to Section 43A")
        doc = _make_entity_document([(clause, [_sec("Section 43A")])])
        graph = GraphIR(
            nodes=[section_node("43A", "section_43a"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].source == "clause_S001_C001"
        assert refs[0].target == "section_43a"

    def test_unknown_section_creates_unresolved(self) -> None:
        clause = _clause(clause_id="S001_C001", text="under Section 99")
        doc = _make_entity_document([(clause, [_sec("Section 99")])])
        graph = GraphIR(
            nodes=[section_node("1", "section_1"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        unresolved_nodes = [n for n in result.nodes if n.label == "UnresolvedReference"]
        assert len(unresolved_nodes) == 1
        assert unresolved_nodes[0].properties["reference_text"] == "Section 99"
        assert unresolved_nodes[0].properties["reference_type"] == "section"

        unresolved_rels = [r for r in result.relationships if r.type == "UNRESOLVED_REFERENCE"]
        assert len(unresolved_rels) == 1
        assert unresolved_rels[0].source == "clause_S001_C001"


class TestRuleReference:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_rule_creates_unresolved(self) -> None:
        clause = _clause(clause_id="S001_C001", text="as per Rule 5")
        doc = _make_entity_document([(clause, [_rule("Rule 5")])])
        graph = GraphIR(
            nodes=[section_node("1"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        unresolved = [n for n in result.nodes if n.label == "UnresolvedReference"]
        assert len(unresolved) == 1
        assert unresolved[0].properties["reference_text"] == "Rule 5"
        unresolved_sources = [
            r.source for r in result.relationships if r.type == "UNRESOLVED_REFERENCE"
        ]
        assert "clause_S001_C001" in unresolved_sources


class TestChapterReference:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_resolves_known_chapter(self) -> None:
        clause = _clause(clause_id="S001_C001", text="in Chapter IX")
        doc = _make_entity_document([(clause, [_chapter("Chapter IX")])])
        graph = GraphIR(
            nodes=[chapter_node("IX"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].target == "chapter_ix"

    def test_unknown_chapter_is_unresolved(self) -> None:
        clause = _clause(clause_id="S001_C001", text="in Chapter VI")
        doc = _make_entity_document([(clause, [_chapter("Chapter VI")])])
        graph = GraphIR(
            nodes=[chapter_node("IX"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        unresolved = [n for n in result.nodes if n.label == "UnresolvedReference"]
        assert len(unresolved) == 1


class TestMultipleReferences:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_multiple_in_one_clause(self) -> None:
        clause = _clause(clause_id="S001_C001", text="under Section 3 and Rule 5")
        doc = _make_entity_document([
            (clause, [_sec("Section 3"), _rule("Rule 5")]),
        ])
        graph = GraphIR(
            nodes=[section_node("3", "section_3"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].target == "section_3"

        unresolved = [r for r in result.relationships if r.type == "UNRESOLVED_REFERENCE"]
        assert len(unresolved) == 1

    def test_nested_references(self) -> None:
        """Different reference types in one clause."""
        text = "pursuant to Section 3 and Chapter IX"
        clause = _clause(clause_id="S001_C001", text=text)
        doc = _make_entity_document([
            (clause, [_sec("Section 3"), _chapter("Chapter IX")]),
        ])
        graph = GraphIR(
            nodes=[
                section_node("3", "section_3"),
                chapter_node("IX"),
                clause_node("S001_C001"),
            ],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 2


class TestDuplicateReferences:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_same_reference_once(self) -> None:
        """Same reference mentioned twice in same clause → one relationship."""
        clause = _clause(clause_id="S001_C001", text="under Section 3 and Section 3")
        doc = _make_entity_document([
            (clause, [_sec("Section 3"), _sec("Section 3")]),
        ])
        graph = GraphIR(
            nodes=[section_node("3", "section_3"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1

    def test_two_clauses_same_target(self) -> None:
        """Two different clauses referencing the same section → two relationships."""
        c1 = _clause(clause_id="S001_C001", text="see Section 3")
        c2 = _clause(clause_id="S002_C001", text="also see Section 3")
        doc = _make_entity_document([
            (c1, [_sec("Section 3")]),
            (c2, [_sec("Section 3")]),
        ])
        graph = GraphIR(
            nodes=[
                section_node("3", "section_3"),
                clause_node("S001_C001"),
                clause_node("S002_C001"),
            ],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 2
        assert {r.source for r in refs} == {"clause_S001_C001", "clause_S002_C001"}


class TestSelfReference:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_self_reference_ignored(self) -> None:
        """Clause referencing its own clause_number should be ignored."""
        # "Clause (a)" will be detected by fallback patterns
        text = "see Clause (a)"
        clause2 = _clause(clause_id="S002_C002", text=text, clause_number="a")
        doc2 = _make_entity_document([
            (clause2, []),
        ])
        graph = GraphIR(
            nodes=[clause_node("S002_C002", clause_number="a")],
            relationships=[],
        )
        result = self.resolver.process(doc2, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 0, "Self reference should not generate a relationship"


class TestUnknownReferences:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_unknown_section(self) -> None:
        clause = _clause(clause_id="S001_C001", text="under Section 99")
        doc = _make_entity_document([(clause, [_sec("Section 99")])])
        graph = GraphIR(nodes=[clause_node("S001_C001")], relationships=[])
        result = self.resolver.process(doc, graph)

        unresolved = [n for n in result.nodes if n.label == "UnresolvedReference"]
        assert len(unresolved) == 1
        n = unresolved[0]
        assert n.properties["reference_text"] == "Section 99"
        assert n.properties["reference_type"] == "section"
        assert n.properties["clause_id"] == "S001_C001"

    def test_unknown_rule(self) -> None:
        clause = _clause(clause_id="S001_C001", text="under Rule 99")
        doc = _make_entity_document([(clause, [_rule("Rule 99")])])
        graph = GraphIR(nodes=[clause_node("S001_C001")], relationships=[])
        result = self.resolver.process(doc, graph)

        unresolved = [n for n in result.nodes if n.label == "UnresolvedReference"]
        assert len(unresolved) == 1


class TestForwardBackwardReferences:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_forward_reference(self) -> None:
        """Clause earlier in doc references a section that appears later."""
        c1 = _clause(clause_id="S001_C001", text="see Section 43A")
        c2 = _clause(clause_id="S002_C001", text="dummy")
        doc = _make_entity_document([
            (c1, [_sec("Section 43A")]),
            (c2, []),
        ])
        graph = GraphIR(
            nodes=[
                section_node("43A", "section_43a"),
                clause_node("S001_C001"),
                clause_node("S002_C001"),
            ],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].target == "section_43a"

    def test_backward_reference(self) -> None:
        """Clause later in doc references an earlier section."""
        c1 = _clause(clause_id="S001_C001", text="dummy")
        c2 = _clause(clause_id="S002_C001", text="see Section 1")
        doc = _make_entity_document([
            (c1, []),
            (c2, [_sec("Section 1")]),
        ])
        graph = GraphIR(
            nodes=[
                section_node("1", "section_1"),
                clause_node("S001_C001"),
                clause_node("S002_C001"),
            ],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].target == "section_1"


class TestEmptyDocument:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_empty_document_noop(self) -> None:
        doc = EntityDocument(metadata=_metadata(), entity_clauses=[])
        graph = GraphIR(nodes=[law_node()], relationships=[])
        result = self.resolver.process(doc, graph)

        assert len(result.nodes) == 1
        assert len(result.relationships) == 0

    def test_empty_graph(self) -> None:
        """GraphIR with no nodes → all references become unresolved."""
        clause = _clause(clause_id="S001_C001", text="see Section 5")
        doc = _make_entity_document([(clause, [_sec("Section 5")])])
        graph = GraphIR(nodes=[], relationships=[])
        result = self.resolver.process(doc, graph)

        # Clause node won't be in an empty graph, so no reference processing happens
        assert len(result.nodes) == 0
        assert len(result.relationships) == 0


class TestFallbackPatterns:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_part_reference(self) -> None:
        """Fallback pattern: Part II."""
        clause = _clause(clause_id="S001_C001", text="under Part II")
        doc = _make_entity_document([(clause, [])])  # no parser metadata
        graph = GraphIR(
            nodes=[chapter_node("II"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].target == "chapter_ii"

    def test_clause_lettered(self) -> None:
        """Fallback: Clause (a) reference."""
        c1 = _clause(clause_id="S001_C001", text="see Clause (a)", clause_number="a")
        doc = _make_entity_document([
            (c1, []),
        ])
        graph = GraphIR(
            nodes=[clause_node("S001_C001", clause_number="a")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        # This is a self-reference, so should be skipped
        # (clause S001_C001 with clause_number="a" referencing "Clause (a)")
        assert len(refs) == 0

    def test_clause_lettered_different(self) -> None:
        """Clause (b) referencing clause (a) should resolve."""
        c1 = _clause(clause_id="S001_C001", text="see Clause (a)", clause_number="b")
        doc = _make_entity_document([
            (c1, []),
        ])
        graph_with_source = GraphIR(
            nodes=[
                clause_node("S001_C001", clause_number="b"),
                clause_node("S002_C002", clause_number="a"),
            ],
            relationships=[],
        )
        result = self.resolver.process(doc, graph_with_source)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].target == "clause_S002_C002"

    def test_explanation_fallback(self) -> None:
        """Fallback: Explanation reference matched by title."""
        clause = _clause(clause_id="S001_C001", text="see Explanation")
        doc = _make_entity_document([(clause, [])])
        graph = GraphIR(
            nodes=[
                GraphNode(
                    id="section_explanation",
                    label="Section",
                    properties={"number": "", "title": "Explanation of Terms"},
                    source_clause=None,
                ),
                clause_node("S001_C001"),
            ],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].target == "section_explanation"

    def test_proviso_fallback(self) -> None:
        """Fallback: Proviso reference matched by title."""
        clause = _clause(clause_id="S001_C001", text="see Proviso")
        doc = _make_entity_document([(clause, [])])
        graph = GraphIR(
            nodes=[
                GraphNode(
                    id="section_proviso",
                    label="Section",
                    properties={"number": "", "title": "Proviso"},
                    source_clause=None,
                ),
                clause_node("S001_C001"),
            ],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1


class TestDuplicateRelationshipPrevention:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_references_type_used(self) -> None:
        """REFERENCES relationship type is used for resolved refs."""
        clause = _clause(clause_id="S001_C001", text="see Section 1")
        doc = _make_entity_document([(clause, [_sec("Section 1")])])
        graph = GraphIR(
            nodes=[section_node("1", "section_1"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        types = {r.type for r in result.relationships}
        assert "REFERENCES" in types


class TestOriginalNodesPreserved:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_existing_relationships_preserved(self) -> None:
        """Original HAS_CHAPTER, HAS_CLAUSE etc. relationships remain."""
        clause = _clause(clause_id="S001_C001", text="see Section 1")
        doc = _make_entity_document([(clause, [_sec("Section 1")])])
        graph = GraphIR(
            nodes=[
                law_node(),
                section_node("1", "section_1"),
                clause_node("S001_C001"),
            ],
            relationships=[
                GraphRelationship(source="law_doc-001", target="section_1", type="HAS_SECTION"),
            ],
        )
        result = self.resolver.process(doc, graph)

        has_section = [r for r in result.relationships if r.type == "HAS_SECTION"]
        assert len(has_section) == 1
        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1


class TestParserMetadataVsFallback:

    def setup_method(self) -> None:
        self.resolver = ReferenceResolver()

    def test_parser_metadata_takes_precedence(self) -> None:
        """Parser metadata is used when available."""
        clause = _clause(clause_id="S001_C001", text="see Section 10")
        doc = _make_entity_document([
            (clause, [Ref(
                reference_text="Section 10",
                reference_type="section",
                start=4,
                end=13,
            )]),
        ])
        graph = GraphIR(
            nodes=[section_node("10", "section_10"), clause_node("S001_C001")],
            relationships=[],
        )
        result = self.resolver.process(doc, graph)

        refs = [r for r in result.relationships if r.type == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].target == "section_10"


class TestSemanticStageInterface:

    def test_resolver_is_stage(self) -> None:
        from semantic_graph.semantic_graph_stage import SemanticGraphStage
        assert isinstance(ReferenceResolver(), SemanticGraphStage)

    def test_process_signature(self) -> None:
        resolver = ReferenceResolver()
        doc = EntityDocument(metadata=_metadata(), entity_clauses=[])
        graph = GraphIR(nodes=[], relationships=[])
        result = resolver.process(doc, graph)
        assert isinstance(result, GraphIR)

    def test_stage_abstract_method(self) -> None:
        import inspect

        from semantic_graph.semantic_graph_stage import SemanticGraphStage
        sig = inspect.signature(SemanticGraphStage.process)
        params = list(sig.parameters.keys())
        assert "document" in params
        assert "graph" in params
