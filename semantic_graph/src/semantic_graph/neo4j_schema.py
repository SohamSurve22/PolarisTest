"""Canonical Neo4j node labels and relationship types for the semantic graph.

All node-creation and relationship-creation code should reference these
constants instead of hardcoding strings, making schema changes centralised.
"""

from __future__ import annotations


class NodeLabel:
    """Neo4j node labels used by the semantic graph exporter.

    Each constant represents the label applied to a Neo4j node created
    from the corresponding ``GraphIR`` node.
    """

    DOCUMENT = "Document"
    ACT = "Act"
    CHAPTER = "Chapter"
    PART = "Part"
    SECTION = "Section"
    CLAUSE = "Clause"
    ENTITY = "Entity"
    OBLIGATION = "Obligation"
    UNRESOLVED_REFERENCE = "UnresolvedReference"


class RelType:
    """Neo4j relationship types used by the semantic graph exporter.

    Each constant represents the type applied to a Neo4j relationship
    created from the corresponding ``GraphIR`` relationship.
    """

    CONTAINS = "CONTAINS"
    HAS_CLAUSE = "HAS_CLAUSE"
    HAS_OBLIGATION = "HAS_OBLIGATION"
    REFERENCES = "REFERENCES"
    MENTIONS = "MENTIONS"
    REFERS_TO = "REFERS_TO"
