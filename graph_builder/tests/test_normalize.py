"""Tests for entity and relation normalization."""

from graph_builder.normalize import canonical_relation_type, normalize_entity, normalize_relation


class TestNormalizeEntity:
  def test_email_maps_to_personal_data(self) -> None:
    entity = normalize_entity("email")
    assert entity.status == "ok"
    assert entity.label == "PersonalData"
    assert entity.canonical_name == "email_address"

  def test_email_address_phrase(self) -> None:
    entity = normalize_entity("your email address")
    assert entity.status == "ok"
    assert entity.label == "PersonalData"

  def test_unknown_entity_is_unmapped(self) -> None:
    entity = normalize_entity("quantum flux capacitor")
    assert entity.status == "UNMAPPED"


class TestNormalizeRelation:
  def test_gathers_maps_to_collects(self) -> None:
    assert canonical_relation_type("gathers") == "COLLECTS"
    assert normalize_relation("gathers", "Actor", "PersonalData") == "COLLECTS"

  def test_owns_is_unmapped(self) -> None:
    assert canonical_relation_type("owns") is None
    assert normalize_relation("owns", "Entity", "PersonalData") is None

  def test_sells_is_unmapped_pending_legal_review(self) -> None:
    assert canonical_relation_type("sells") is None
