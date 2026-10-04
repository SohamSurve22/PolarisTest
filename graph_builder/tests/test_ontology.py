"""Tests for Ideal Graph schema triples and alias loaders."""

from graph_builder.graph_models import ALLOWED_NODE_LABELS, ALLOWED_RELATIONSHIP_TYPES
from graph_builder.ontology import (
  ALLOWED_TRIPLES,
  load_entity_aliases,
  load_relation_aliases,
  triple_allowed,
)


class TestAllowedTriples:
  def test_every_triple_uses_allowed_vocabulary(self) -> None:
    for source, rel, target in ALLOWED_TRIPLES:
      assert source in ALLOWED_NODE_LABELS
      assert rel in ALLOWED_RELATIONSHIP_TYPES
      assert target in ALLOWED_NODE_LABELS

  def test_collects_actor_to_personal_data(self) -> None:
    assert triple_allowed("Actor", "COLLECTS", "PersonalData")
    assert triple_allowed("Entity", "COLLECTS", "SensitiveData")

  def test_owns_is_not_a_triple(self) -> None:
    assert not triple_allowed("Entity", "OWNS", "PersonalData")

  def test_sample_ir_triples_are_allowed(self) -> None:
    assert triple_allowed("LawVersion", "HAS_SECTION", "Section")
    assert triple_allowed("Section", "IMPOSES", "Obligation")
    assert triple_allowed("Clause", "HAS_OBLIGATION", "Obligation")


class TestAliases:
  def test_relation_aliases_map_gathers_to_collects(self) -> None:
    aliases = load_relation_aliases()
    assert aliases["gathers"] == "COLLECTS"
    assert aliases["collect"] == "COLLECTS"
    assert "sells" not in aliases

  def test_entity_aliases_map_email_to_personal_data(self) -> None:
    aliases = load_entity_aliases()
    email = aliases["email"]
    assert email["canonical_name"] == "email_address"
    assert email["label"] == "PersonalData"
    assert aliases["email address"]["canonical_name"] == "email_address"
