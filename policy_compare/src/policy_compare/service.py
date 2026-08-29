"""Compare an EntityDocument against the projected ideal law graph."""

from __future__ import annotations

from pathlib import Path

from document_pipeline.models.entity import EntityDocument
from document_pipeline.models.section import SectionedDocument

from policy_compare.clustering import cluster_policy_graph
from policy_compare.law_loader import load_law_chunks
from policy_compare.matcher import match_graphs
from policy_compare.models import MatchResult
from policy_compare.policy_view import policy_view_graph
from policy_compare.projection import project_ideal_graph

DEFAULT_LAW_FILES = (
  "dpdp_graph.json",
  "spdi_graph.json",
  "certin_graph.json",
  "itact_graph.json",
)


def default_law_paths(repo_root: Path) -> list[Path]:
  return [repo_root / name for name in DEFAULT_LAW_FILES]


def compare_document(
  document: EntityDocument,
  law_paths: list[Path],
  sectioned: SectionedDocument | None = None,
) -> MatchResult:
  chunks = load_law_chunks(law_paths)
  ideal = project_ideal_graph(chunks)
  policy = policy_view_graph(document, sectioned)
  matched = match_graphs(policy, ideal, chunks)
  clustered = cluster_policy_graph(matched.policy, matched.links)
  return MatchResult(policy=clustered, ideal=matched.ideal, links=matched.links)
