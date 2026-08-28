from pathlib import Path

from policy_compare.law_loader import load_law_chunks
from policy_compare.topics import KEPT_TOPICS

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_law.json"


def test_load_keeps_consent_obligation() -> None:
  chunks = load_law_chunks([FIXTURE])
  ids = {chunk.doc_id for chunk in chunks}
  assert "TINY_CONSENT" in ids
  consent = next(chunk for chunk in chunks if chunk.doc_id == "TINY_CONSENT")
  assert "TOPIC_CONSENT" in consent.topic_ids
  assert set(consent.topic_ids) <= KEPT_TOPICS


def test_load_drops_governance_and_it_act_signature() -> None:
  chunks = load_law_chunks([FIXTURE])
  ids = {chunk.doc_id for chunk in chunks}
  assert "TINY_GOVERNANCE" not in ids
  assert "TINY_SIGNATURE" not in ids
  assert "DOC_TINY" not in ids
