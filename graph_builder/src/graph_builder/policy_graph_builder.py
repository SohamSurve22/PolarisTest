"""Build policy GraphIR from OpenIE propositions constrained by the Ideal schema."""

from __future__ import annotations

from typing import TYPE_CHECKING

from graph_builder.graph_ir import GraphIR, GraphNode, GraphRelationship
from graph_builder.mapping_failures import MappingFailure, MappingStatus
from graph_builder.normalize import (
  CanonicalEntity,
  canonical_relation_type,
  is_context_predicate,
  normalize_entity,
  normalize_relation,
)
from graph_builder.openie import OpenIEExtractor
from graph_builder.propositions import RawProposition

if TYPE_CHECKING:
  from document_pipeline.models.entity import EntityDocument


class PolicyGraphBuilder:
  """OpenIE → normalize → GraphIR. Unknown vocabulary becomes MappingFailure."""

  def __init__(self, extractor: OpenIEExtractor) -> None:
    self._extractor = extractor

  def build(self, entity_document: EntityDocument) -> tuple[GraphIR, list[MappingFailure]]:
    propositions = self._extractor.extract(entity_document)
    return propositions_to_graph_ir(
      propositions,
      document_id=entity_document.metadata.document_id,
    )


def propositions_to_graph_ir(
  propositions: list[RawProposition],
  *,
  document_id: str = "",
) -> tuple[GraphIR, list[MappingFailure]]:
  nodes: dict[str, GraphNode] = {}
  relationships: list[GraphRelationship] = []
  failures: list[MappingFailure] = []
  seen_edges: set[tuple[str, str, str]] = set()
  context_by_clause: dict[str, dict[str, str]] = {}

  for prop in propositions:
    if is_context_predicate(prop.predicate):
      _store_context(context_by_clause, prop)
      continue

    subject = normalize_entity(prop.subject)
    obj = normalize_entity(prop.object)
    subject_fail = _entity_failure(prop, subject, role="subject", document_id=document_id)
    object_fail = _entity_failure(prop, obj, role="object", document_id=document_id)
    if subject_fail is not None:
      failures.append(subject_fail)
    if object_fail is not None:
      failures.append(object_fail)
    if subject.status != "ok" or obj.status != "ok":
      continue

    canonical = canonical_relation_type(prop.predicate)
    if canonical is None:
      failures.append(
        _failure(
          prop,
          status="UNMAPPED_RELATION",
          reason="No compatible canonical relation found",
          document_id=document_id,
        ),
      )
      continue

    rel = normalize_relation(prop.predicate, subject.label, obj.label)
    if rel is None:
      failures.append(
        _failure(
          prop,
          status="INVALID_RELATION_COMBINATION",
          reason=(
            f"{subject.label} -[{canonical}]-> {obj.label} "
            "is not an allowed Ideal Graph triple"
          ),
          document_id=document_id,
        ),
      )
      continue

    source_id = _node_id(subject)
    target_id = _node_id(obj)
    _ensure_node(nodes, subject, source_id, prop)
    _ensure_node(nodes, obj, target_id, prop)
    edge_key = (source_id, rel, target_id)
    if edge_key in seen_edges:
      continue
    seen_edges.add(edge_key)
    extra: dict[str, object] = dict(context_by_clause.get(prop.source_clause_id, {}))
    extra["evidence"] = prop.evidence
    extra["clause_id"] = prop.source_clause_id
    if prop.confidence is not None:
      extra["confidence"] = prop.confidence
    relationships.append(
      GraphRelationship(
        source=source_id,
        target=target_id,
        type=rel,
        properties=extra,
      ),
    )

  return GraphIR(nodes=list(nodes.values()), relationships=relationships), failures


def _store_context(
  context_by_clause: dict[str, dict[str, str]],
  prop: RawProposition,
) -> None:
  bucket = context_by_clause.setdefault(prop.source_clause_id, {})
  lowered = prop.predicate.lower()
  if "purpose" in lowered or lowered == "for":
    bucket["purpose"] = prop.object
  elif "duration" in lowered or "as long as" in lowered:
    bucket["duration"] = prop.object
  else:
    bucket[prop.predicate] = prop.object


def _node_id(entity: CanonicalEntity) -> str:
  return f"{entity.label}:{entity.canonical_name}"


def _ensure_node(
  nodes: dict[str, GraphNode],
  entity: CanonicalEntity,
  node_id: str,
  prop: RawProposition,
) -> None:
  if node_id in nodes:
    return
  nodes[node_id] = GraphNode(
    id=node_id,
    label=entity.label,
    properties={"name": entity.canonical_name},
    source_clause=prop.source_clause_id or None,
  )


def _entity_failure(
  prop: RawProposition,
  entity: CanonicalEntity,
  *,
  role: str,
  document_id: str,
) -> MappingFailure | None:
  if entity.status == "ok":
    return None
  status: MappingStatus = (
    "AMBIGUOUS_ENTITY" if entity.status == "AMBIGUOUS" else "UNMAPPED_ENTITY"
  )
  raw = prop.subject if role == "subject" else prop.object
  return _failure(
    prop,
    status=status,
    reason=f"{role} {raw!r} is not a canonical Ideal Graph entity",
    document_id=document_id,
  )


def _failure(
  prop: RawProposition,
  *,
  status: MappingStatus,
  reason: str,
  document_id: str,
) -> MappingFailure:
  return MappingFailure(
    status=status,
    raw_predicate=prop.predicate,
    subject=prop.subject,
    object=prop.object,
    evidence=prop.evidence,
    reason=reason,
    source_clause_id=prop.source_clause_id,
    document_id=document_id or prop.document_id,
    confidence=prop.confidence,
  )
