"""Dense and graph retrievers for statute Q&A."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from vectorization.models import SearchHit

from rag.models import RagCitation

SearchFn = Callable[..., list[SearchHit]]

DENSE_TOP_K = 5
GRAPH_SEED_K = 5
GRAPH_CONTEXT_CAP = 8
RAG_MIN_SCORE = 0.0


def citations_from_hits(
  hits: list[SearchHit],
  *,
  allowed_source_types: tuple[str, ...] | None = None,
) -> list[RagCitation]:
  rows: list[RagCitation] = []
  seen: set[str] = set()
  for hit in hits:
    if allowed_source_types and hit.source_type not in allowed_source_types:
      continue
    cid = _citation_id(hit)
    if not cid or cid in seen:
      continue
    seen.add(cid)
    payload = hit.payload or {}
    title = str(payload.get("title") or payload.get("section_title") or "")
    text = (hit.retrieval_text or hit.clause_text or "").strip()
    rows.append(RagCitation(id=cid, title=title, text=text, score=hit.score))
  return rows


def retrieve_dense(question: str, *, search: SearchFn) -> list[RagCitation]:
  hits = search(
    question,
    source_type="rag_section",
    top_k=DENSE_TOP_K,
    min_score=RAG_MIN_SCORE,
  )
  return citations_from_hits(hits, allowed_source_types=("rag_section",))


def retrieve_graph(
  question: str,
  *,
  search: SearchFn,
  ir=None,
  law_paths: list[Path] | None = None,
  cap: int = GRAPH_CONTEXT_CAP,
) -> list[RagCitation]:
  hits = search(
    question,
    source_type="kg_obligation",
    top_k=GRAPH_SEED_K,
    min_score=RAG_MIN_SCORE,
  )
  allowed: tuple[str, ...] = ("kg_obligation",)
  if not hits:
    hits = search(
      question,
      source_type="kg_section",
      top_k=GRAPH_SEED_K,
      min_score=RAG_MIN_SCORE,
    )
    allowed = ("kg_section",)
  citations = citations_from_hits(hits, allowed_source_types=allowed)
  graph = ir if ir is not None else _load_ir(law_paths)
  if graph is None:
    return citations[:cap]
  return _expand_graph(citations, graph, cap=cap)


def _citation_id(hit: SearchHit) -> str:
  payload = hit.payload or {}
  return str(
    payload.get("obligation_id")
    or hit.clause_id
    or payload.get("clause_id")
    or payload.get("section_id")
    or hit.section_id
    or ""
  )


def _load_ir(law_paths: list[Path] | None):
  from compliance.graph_scope import ir_from_paths
  from policy_compare.service import default_law_paths

  paths = law_paths
  if not paths:
    root = Path(__file__).resolve().parents[3]
    paths = default_law_paths(root)
  if not paths or not all(path.is_file() for path in paths):
    return None
  return ir_from_paths(paths)


def _expand_graph(seeds: list[RagCitation], ir, *, cap: int) -> list[RagCitation]:
  obligations = {node.id: node for node in ir.nodes if node.label == "Obligation"}
  out = list(seeds[:cap])
  seen = {row.id for row in out}
  floor = min((row.score for row in seeds), default=0.0) - 0.01
  for oid in _neighbor_ids(ir, [row.id for row in seeds], obligations):
    if oid in seen or len(out) >= cap:
      continue
    node = obligations.get(oid)
    if node is None:
      continue
    props = node.properties or {}
    text = str(props.get("text") or props.get("summary") or "").strip()
    if not text:
      continue
    seen.add(oid)
    out.append(
      RagCitation(
        id=oid,
        title=str(props.get("title") or ""),
        text=text,
        score=floor,
      )
    )
  return out


def _neighbor_ids(ir, seed_ids: list[str], obligations: dict) -> list[str]:
  penalty_targets: dict[str, list[str]] = {}
  for rel in ir.relationships:
    if rel.type == "PENALIZES":
      penalty_targets.setdefault(rel.source, []).append(rel.target)

  ordered: list[str] = []
  seen: set[str] = set()

  def add(oid: str) -> None:
    if oid in seen or oid in seed_ids:
      return
    seen.add(oid)
    ordered.append(oid)

  for sid in seed_ids:
    for targets in penalty_targets.values():
      if sid in targets:
        for oid in targets:
          add(oid)
    seed = obligations.get(sid)
    section = _section_key(sid, seed)
    if not section:
      continue
    for oid, node in obligations.items():
      if _section_key(oid, node) == section:
        add(oid)
  return ordered


def _section_key(oid: str, node) -> str | None:
  props = (node.properties or {}) if node is not None else {}
  section = props.get("section_id")
  if section:
    return str(section)
  if "_SUB_" in oid:
    return oid.rsplit("_SUB_", 1)[0]
  return None
