"""Comprehensive tests for ``HierarchyBuilder``."""

from __future__ import annotations

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship

from semantic_graph.hierarchy_builder import HierarchyBuilder

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_metadata(
    *,
    document_id: str = "doc-001",
    title: str = "Test Law",
) -> DocumentMetadata:
    return DocumentMetadata(
        document_id=document_id,
        filename="test.txt",
        format=DocumentFormat.TXT,
        title=title,
    )


def _make_clause(
    *,
    clause_id: str,
    section_id: str,
    section_title: str | None = None,
    text: str = "",
    clause_number: str | None = None,
    document_id: str = "doc-001",
) -> Clause:
    return Clause(
        clause_id=clause_id,
        section_id=section_id,
        section_title=section_title,
        document_id=document_id,
        document_type=DocumentFormat.TXT,
        clause_text=text,
        span=Span(start=0, end=len(text)),
        clause_number=clause_number,
    )


def _make_classified(clause: Clause) -> ClassifiedClause:
    return ClassifiedClause(
        clause=clause,
        role=StructuralRole.STATEMENT,
        confidence=1.0,
        classification_reason=["test"],
    )


def _make_entity_clause(clause: Clause) -> EntityClause:
    classified = _make_classified(clause)
    contextual = ContextualClause(
        classified_clause=classified,
        previous_clause_id=None,
        next_clause_id=None,
        section_position=0,
        is_first_in_section=True,
        is_last_in_section=True,
        neighbor_clause_ids=[],
        detected_references=[],
    )
    return EntityClause(
        contextual_clause=contextual,
        entities=[],
    )


def _make_document(
    clauses: list[Clause],
    *,
    document_id: str = "doc-001",
    title: str = "Test Law",
) -> EntityDocument:
    return EntityDocument(
        metadata=_make_metadata(document_id=document_id, title=title),
        entity_clauses=[_make_entity_clause(c) for c in clauses],
    )


def find_node(ir: GraphIR, label: str) -> list[GraphNode]:
    return [n for n in ir.nodes if n.label == label]


def find_rels(ir: GraphIR, rel_type: str) -> list[GraphRelationship]:
    return [r for r in ir.relationships if r.type == rel_type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSimpleHierarchy:
    """A single chapter with one section containing one clause."""

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_simple_hierarchy(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001",
                section_id="S001",
                section_title="CHAPTER 1: Introduction",
                text="This is a clause.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        assert len(ir.nodes) == 3  # LawVersion + Chapter + Clause
        assert len(ir.relationships) == 2  # Law→Chapter + Chapter→Clause (skip Section/SubSection)

    def test_has_law_version_node(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001",
                section_id="S001",
                section_title="CHAPTER 1",
                text="Clause text.",
            ),
        ]
        doc = _make_document(clauses, document_id="doc-a", title="Test Act")
        ir = self.builder.build(doc)

        law_nodes = find_node(ir, "LawVersion")
        assert len(law_nodes) == 1
        assert law_nodes[0].id == "law_doc-a"
        assert law_nodes[0].properties["law_code"] == "doc-a"
        assert law_nodes[0].properties["title"] == "Test Act"

    def test_has_chapter_node(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001",
                section_id="S001",
                section_title="CHAPTER 1: Introduction",
                text="Clause text.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        chapters = find_node(ir, "Chapter")
        assert len(chapters) == 1
        assert chapters[0].id == "chapter_S001"
        assert chapters[0].properties["number"] == "1"
        assert "Introduction" in str(chapters[0].properties["title"])

    def test_has_clause_node(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001",
                section_id="S001",
                section_title="CHAPTER 1",
                text="The actual clause content.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        clause_nodes = find_node(ir, "Clause")
        assert len(clause_nodes) == 1
        assert clause_nodes[0].id == "clause_S001_C001"
        assert clause_nodes[0].properties["text"] == "The actual clause content."
        assert clause_nodes[0].properties["confidence"] == 1.0
        assert clause_nodes[0].properties["clause_id"] == "S001_C001"


class TestMultipleChapters:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_two_chapters(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1: Intro", text="Chapter 1 clause.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="CHAPTER 2: Scope", text="Chapter 2 clause.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        chapters = find_node(ir, "Chapter")
        assert len(chapters) == 2
        assert chapters[0].properties["number"] == "1"
        assert chapters[1].properties["number"] == "2"

    def test_chapter_to_chapter_relationship(self) -> None:
        """Each chapter should connect to LawVersion."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="C1.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="CHAPTER 2", text="C2.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        has_chapter = find_rels(ir, "HAS_CHAPTER")
        assert len(has_chapter) == 2

        law = find_node(ir, "LawVersion")[0]
        for rel in has_chapter:
            assert rel.source == law.id


class TestMultipleSections:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_sections_under_chapter(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="Intro.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="1. Scope", text="Scope clause.",
            ),
            _make_clause(
                clause_id="S003_C001", section_id="S003",
                section_title="2. Definitions", text="Definitions clause.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        chapters = find_node(ir, "Chapter")
        sections = find_node(ir, "Section")
        assert len(chapters) == 1
        assert len(sections) == 2

        # Sections should connect to the Chapter (HAS_SECTION)
        has_section = find_rels(ir, "HAS_SECTION")
        chapter_id = chapters[0].id
        for rel in has_section:
            assert rel.source == chapter_id


class TestNestedSubsections:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_section_with_subsections(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="Chapter clause.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="1. Scope", text="Section clause.",
            ),
            _make_clause(
                clause_id="S003_C001", section_id="S003",
                section_title="1.1 Applicability", text="Subsection clause.",
            ),
            _make_clause(
                clause_id="S004_C001", section_id="S004",
                section_title="1.2 Exceptions", text="Another subsection.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        assert len(find_node(ir, "Chapter")) == 1
        assert len(find_node(ir, "Section")) == 1
        assert len(find_node(ir, "SubSection")) == 2
        assert len(find_node(ir, "Clause")) == 4

        # Subsections should connect to Section via HAS_SUBSECTION
        has_subsection = find_rels(ir, "HAS_SUBSECTION")
        assert len(has_subsection) == 2
        section_id = "section_S002"
        for rel in has_subsection:
            assert rel.source == section_id

    def test_deeply_nested(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="C1.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="1. Section One", text="S1.",
            ),
            _make_clause(
                clause_id="S003_C001", section_id="S003",
                section_title="1.1 Sub A", text="SS1.",
            ),
            _make_clause(
                clause_id="S004_C001", section_id="S004",
                section_title="1.1.1 SubSub A", text="SSS1.",
            ),
            _make_clause(
                clause_id="S005_C001", section_id="S005",
                section_title="1.2 Sub B", text="SS2.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        assert len(find_node(ir, "Chapter")) == 1
        assert len(find_node(ir, "Section")) == 1
        # 1.1, 1.1.1, 1.2 all become SubSection
        assert len(find_node(ir, "SubSection")) == 3


class TestDocumentsWithoutChapters:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_sections_only(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="1. Scope", text="Scope clause.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="2. Definitions", text="Defs.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        assert len(find_node(ir, "LawVersion")) == 1
        assert len(find_node(ir, "Chapter")) == 0
        assert len(find_node(ir, "Section")) == 2
        assert len(find_node(ir, "Clause")) == 2

        # Sections connect directly to LawVersion
        has_section = find_rels(ir, "HAS_SECTION")
        assert len(has_section) == 2
        law = find_node(ir, "LawVersion")[0]
        for rel in has_section:
            assert rel.source == law.id

    def test_no_headers(self) -> None:
        """Sections without explicit chapter/heading indicators default to Section."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title=None, text="Some content.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        assert len(find_node(ir, "Section")) == 1
        assert len(find_node(ir, "Chapter")) == 0

    def test_roman_numeral_section(self) -> None:
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="I. Preliminary", text="Prelim.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="II. Definitions", text="Defs.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        assert len(find_node(ir, "Section")) == 2
        assert len(find_node(ir, "Chapter")) == 0


class TestDuplicateDetection:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_same_section_multiple_clauses(self) -> None:
        """Multiple clauses in the same section → one hierarchy node."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="1. Scope", text="First clause.",
            ),
            _make_clause(
                clause_id="S001_C002", section_id="S001",
                section_title="1. Scope", text="Second clause.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        sections = find_node(ir, "Section")
        assert len(sections) == 1

        clauses_nodes = find_node(ir, "Clause")
        assert len(clauses_nodes) == 2

        # Both clauses should connect to the same section
        has_clause = find_rels(ir, "HAS_CLAUSE")
        assert len(has_clause) == 2
        section_id = sections[0].id
        for rel in has_clause:
            assert rel.source == section_id

    def test_duplicate_section_title(self) -> None:
        """Different section_ids with same title are distinct hierarchy nodes."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="1. Scope", text="Scope A.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="1. Scope", text="Scope B.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        sections = find_node(ir, "Section")
        assert len(sections) == 2
        assert sections[0].id != sections[1].id


class TestOrderingPreservation:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_node_order(self) -> None:
        """Nodes should appear in document order."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="C1.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="1. Section", text="Sec.",
            ),
            _make_clause(
                clause_id="S003_C001", section_id="S003",
                section_title="1.1 Sub", text="Sub.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        node_labels = [n.label for n in ir.nodes]
        # Document order: each section appears before the clauses within it
        expected_order = ["LawVersion", "Chapter", "Clause",
                          "Section", "Clause", "SubSection", "Clause"]
        assert node_labels == expected_order, f"Got {node_labels}"

    def test_relationship_order(self) -> None:
        """Relationships should follow the same order as nodes."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="C1.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="CHAPTER 2", text="C2.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        rel_types = [r.type for r in ir.relationships]
        # Document order: chapter, its clause, next chapter, its clause
        assert rel_types == ["HAS_CHAPTER", "HAS_CLAUSE", "HAS_CHAPTER", "HAS_CLAUSE"]


class TestEmptyDocument:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_empty_clauses_raises(self) -> None:
        doc = EntityDocument(
            metadata=_make_metadata(),
            entity_clauses=[],
        )
        import pytest
        with pytest.raises(ValueError, match="empty"):
            self.builder.build(doc)

    def test_none_clauses_raises(self) -> None:
        doc = EntityDocument(
            metadata=_make_metadata(),
            entity_clauses=[],
        )
        import pytest
        with pytest.raises(ValueError, match="empty"):
            self.builder.build(doc)


class TestInvalidHierarchy:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    def test_skip_level_clause_under_section(self) -> None:
        """Section directly contains Clause (no SubSection)."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="Ch.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="1. Scope", text="Scope.",
            ),
            _make_clause(
                clause_id="S002_C002", section_id="S002",
                section_title="1. Scope", text="More scope.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        has_clause = find_rels(ir, "HAS_CLAUSE")
        # One for Chapter→clause_S001_C001, two for Section→clause_S002_C001/2
        assert len(has_clause) == 3
        section = find_node(ir, "Section")[0]
        section_clause_rels = [r for r in has_clause if r.source == section.id]
        assert len(section_clause_rels) == 2

    def test_skip_to_law_version(self) -> None:
        """Clause directly under LawVersion (no chapters/sections)."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title=None, text="Direct clause.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        section = find_node(ir, "Section")[0]
        has_clause = find_rels(ir, "HAS_CLAUSE")
        assert len(has_clause) == 1
        # Clause connects to Section (nearest valid parent); Section connects to LawVersion
        assert has_clause[0].source == section.id
        has_section = find_rels(ir, "HAS_SECTION")
        assert len(has_section) == 1
        law = find_node(ir, "LawVersion")[0]
        assert has_section[0].source == law.id

    def test_no_orphan_clauses(self) -> None:
        """Every Clause node must have exactly one incoming relationship."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="C1.",
            ),
            _make_clause(
                clause_id="S001_C002", section_id="S001",
                section_title="CHAPTER 1", text="C2.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        clause_ids = {n.id for n in find_node(ir, "Clause")}
        target_ids = {r.target for r in ir.relationships}
        for cid in clause_ids:
            assert cid in target_ids, f"Clause {cid} has no incoming relationship"

    def test_no_cycles(self) -> None:
        """Verify no relationship creates a cycle (simple reachability check)."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="C1.",
            ),
            _make_clause(
                clause_id="S002_C001", section_id="S002",
                section_title="1. Section", text="Sec.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        # Build adjacency: source -> [targets]
        adj: dict[str, list[str]] = {}
        for r in ir.relationships:
            adj.setdefault(r.source, []).append(r.target)
            adj.setdefault(r.target, [])

        # Topological: every edge goes from earlier node to later node in node list
        node_order = {n.id: i for i, n in enumerate(ir.nodes)}
        for r in ir.relationships:
            assert node_order[r.source] < node_order[r.target], (
                f"Cycle detected: {r.source} -> {r.target}"
            )


class TestChapterPrefixVariants:

    def setup_method(self) -> None:
        self.builder = HierarchyBuilder()

    @staticmethod
    def _make_clause(section_id: str, title: str) -> Clause:
        clause_id = f"{section_id}_C001"
        return _make_clause(
            clause_id=clause_id,
            section_id=section_id,
            section_title=title,
            text="Clause content.",
        )

    def test_chapter_lowercase(self) -> None:
        doc = _make_document([self._make_clause("S001", "chapter 1: Intro")])
        ir = self.builder.build(doc)
        assert len(find_node(ir, "Chapter")) == 1

    def test_article_prefix(self) -> None:
        doc = _make_document([self._make_clause("S001", "Article 5: Principles")])
        ir = self.builder.build(doc)
        assert len(find_node(ir, "Chapter")) == 1

    def test_schedule_prefix(self) -> None:
        doc = _make_document([self._make_clause("S001", "Schedule A")])
        ir = self.builder.build(doc)
        assert len(find_node(ir, "Chapter")) == 1

    def test_ch_abbreviation(self) -> None:
        doc = _make_document([self._make_clause("S001", "Ch. 3: Data")])
        ir = self.builder.build(doc)
        assert len(find_node(ir, "Chapter")) == 1

    def test_plain_numbered_becomes_section(self) -> None:
        doc = _make_document([self._make_clause("S001", "1. Application")])
        ir = self.builder.build(doc)
        assert len(find_node(ir, "Section")) == 1
        assert len(find_node(ir, "Chapter")) == 0

    def test_dotted_number_becomes_subsection(self) -> None:
        doc = _make_document([self._make_clause("S001", "1.1 Details")])
        ir = self.builder.build(doc)
        assert len(find_node(ir, "SubSection")) == 1
        assert len(find_node(ir, "Section")) == 0
        assert len(find_node(ir, "Chapter")) == 0


class TestSemanticGraphBuilder:

    def setup_method(self) -> None:
        from semantic_graph.semantic_graph_builder import SemanticGraphBuilder
        self.builder = SemanticGraphBuilder()

    def test_default_construction(self) -> None:
        """SemanticGraphBuilder creates with default HierarchyBuilder."""
        assert self.builder._hierarchy_builder is not None

    def test_build_delegates_to_hierarchy(self) -> None:
        """build() returns a GraphIR with hierarchy structure."""
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="Test.",
            ),
        ]
        doc = _make_document(clauses)
        ir = self.builder.build(doc)

        assert isinstance(ir, GraphIR)
        assert len(ir.nodes) > 1
        assert len(find_node(ir, "LawVersion")) == 1

    def test_inject_custom_hierarchy_builder(self) -> None:
        """Dependency injection of custom builder."""
        from semantic_graph.semantic_graph_builder import SemanticGraphBuilder

        class CustomBuilder:
            def build(self, document: object) -> GraphIR:
                return GraphIR(
                    nodes=[GraphNode(id="custom", label="Custom", properties={})],
                    relationships=[],
                )

        custom = CustomBuilder()
        builder = SemanticGraphBuilder(hierarchy_builder=custom)  # type: ignore[arg-type]
        clauses = [
            _make_clause(
                clause_id="S001_C001", section_id="S001",
                section_title="CHAPTER 1", text="Test.",
            ),
        ]
        doc = _make_document(clauses)
        ir = builder.build(doc)

        assert len(ir.nodes) == 1
        assert ir.nodes[0].id == "custom"
