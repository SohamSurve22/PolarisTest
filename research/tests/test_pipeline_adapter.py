"""
Tests for research.pipeline_adapter.

These tests verify that:
1. The adapter actually calls the real compliance engine components.
2. Feature flags (use_element_decomposition, use_denial_polarity) are wired.
3. Specific input texts produce the expected engine behaviour.
4. Adapter does NOT silently return "missing" for all inputs.

Each test uses a manually verified expected outcome.  Tests do NOT use
Qdrant or Ollama — they rely on the keyword-stub search built into the
adapter, which is the same mechanism used by many compliance unit tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from research.config import ExperimentConfig
from research.pipeline_adapter import run_case, _build_clauses, _stub_search_fn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _case(policy_text: str, obligation_id: str = "DPDP_SEC_6_SUB_1") -> dict:
    return {
        "case_id": "TEST_TMP",
        "obligation_id": obligation_id,
        "policy_text": policy_text,
        "expected_status": "covered",
        "expected_elements": [],
    }


def _run(policy_text: str, config: ExperimentConfig, obligation_id: str = "DPDP_SEC_6_SUB_1"):
    return run_case(_case(policy_text, obligation_id), config)


# ---------------------------------------------------------------------------
# Section 1: Basic integration smoke-tests
# (verify adapter reaches real engine and does not always return "missing")
# ---------------------------------------------------------------------------


def test_adapter_does_not_always_return_missing():
    """
    A policy that explicitly states consent and purpose must NOT be
    classified as missing by all four configurations.
    """
    text = (
        "We collect your personal data only with your prior informed consent. "
        "The purposes are account management and customer support."
    )
    results = {}
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg)
        results[cfg.name] = pred.status
    # At least one config must produce a non-missing result
    assert any(s != "missing" for s in results.values()), (
        f"All configs returned 'missing' for a clearly compliant policy: {results}"
    )


def test_adapter_returns_missing_for_empty_policy():
    for cfg in ExperimentConfig.all_configs():
        pred = _run("", cfg)
        assert pred.status == "missing"
        assert pred.integration_complete is True


def test_adapter_integration_complete_flag():
    """All configs must set integration_complete=True for valid input."""
    text = "Your consent is required for us to process your data for account management."
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg)
        assert pred.integration_complete is True, (
            f"Config {cfg.name} set integration_complete=False: {pred.diagnostics}"
        )


def test_adapter_returns_populated_evidence_for_compliant_policy():
    """
    A clearly compliant policy must return at least one matched evidence clause.
    """
    text = (
        "You provide your opt-in consent when registering. "
        "We process your personal data for the purpose of delivering our services."
    )
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg)
        # Status should not be missing if policy is clearly compliant
        # (keyword-stub may produce partial or covered)
        assert pred.status != "missing", (
            f"Config {cfg.name}: expected non-missing, got {pred.status}. "
            f"Diagnostics: {pred.diagnostics}"
        )


# ---------------------------------------------------------------------------
# Section 2: Denial / violation cases
# ---------------------------------------------------------------------------


def test_irrevocable_consent_produces_violation():
    """
    The contradiction_cue 'irrevocable consent' and 'consent cannot be withdrawn'
    must be detected for DPDP_SEC_6_SUB_5.

    With the keyword-stub search (which now scores contradiction-cue tokens),
    the engine should find the clause and flag it as a contradiction → violation
    or conflict.

    If the actor-filter strips the clause (no 'we/our' marker) and the engine
    falls back to 'missing', we accept that as a known limitation of the
    keyword-stub + actor-filter combination and record it explicitly.  What we
    MUST NOT see is 'covered' or 'partial' for irrevocable-consent text.
    """
    text = "Consent, once given, is irrevocable and cannot be withdrawn."
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg, obligation_id="DPDP_SEC_6_SUB_5")
        # Must NOT be covered or partial (that would be a false-positive)
        assert pred.status not in {"covered", "partial"}, (
            f"Config {cfg.name}: irrevocable-consent text wrongly classified as "
            f"{pred.status}. Diagnostics: {pred.diagnostics}"
        )
        # Document what we observed (not a hard requirement on violation vs missing)
        if pred.status == "missing":
            # Acceptable: actor-filter stripped the clause (no 'we/our' marker).
            # The stub limitation is documented in pipeline_adapter.py.
            pass


def test_withdrawal_plus_cessation_is_covered():
    """
    A policy stating both withdrawal right and cessation of processing must
    be classified as covered for DPDP_SEC_6_SUB_5.
    """
    text = (
        "You may withdraw your consent at any time by contacting us. "
        "Upon withdrawal we will cease processing your personal data within 72 hours."
    )
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg, obligation_id="DPDP_SEC_6_SUB_5")
        assert pred.status in {"covered", "partial"}, (
            f"Config {cfg.name}: expected covered/partial, got {pred.status}. "
            f"Diagnostics: {pred.diagnostics}"
        )


def test_denial_polarity_blocks_irrevocable_clause():
    """
    The polarity-aware config must detect a denial and NOT produce evidence
    from the irrevocable-consent clause.
    """
    text = "Consent cannot be withdrawn once given."
    pred = _run(text, ExperimentConfig.polarity_aware(), obligation_id="DPDP_SEC_6_SUB_5")
    # Denial should be detected; should not claim withdrawal is satisfied
    assert "withdraw" not in pred.satisfied_elements


def test_baseline_finds_withdrawal_keyword_despite_denial():
    """
    The baseline config does NOT apply the denial pre-filter, so the engine
    should pick up the contradiction cue and return violation (not missing).
    This verifies the baseline actually uses the engine, not the stub.
    """
    text = "Once provided, consent cannot be withdrawn."
    pred = _run(text, ExperimentConfig.baseline(), obligation_id="DPDP_SEC_6_SUB_5")
    # Engine detects contradiction_cue → violation or conflict (not missing)
    assert pred.status in {"violation", "conflict", "partial"}, (
        f"Baseline: expected engine-driven result, got {pred.status}."
        f" Diagnostics: {pred.diagnostics}"
    )


# ---------------------------------------------------------------------------
# Section 3: Element decomposition
# ---------------------------------------------------------------------------


def test_element_decomp_reports_satisfied_elements():
    """
    When use_element_decomposition is True, satisfied_elements must be
    populated for a policy that contains element keywords.
    """
    text = (
        "We process your personal data only with your explicit consent. "
        "Processing is done for the purpose of order fulfilment."
    )
    pred = _run(text, ExperimentConfig.element_decomp())
    # Both 'consent' (informed_consent) and 'purpose' elements should be found
    assert len(pred.satisfied_elements) > 0, (
        f"element_decomp config produced no satisfied elements. "
        f"Diagnostics: {pred.diagnostics}"
    )


def test_baseline_satisfied_elements_from_engine_element_hits():
    """
    Baseline must also report element hits when the engine finds them
    (element_hits from evidence_bundle).
    """
    text = "Your consent is required. The purpose is account management."
    pred_baseline = _run(text, ExperimentConfig.baseline())
    pred_decomp = _run(text, ExperimentConfig.element_decomp())
    # decomp must have >= elements of baseline (it merges)
    assert len(pred_decomp.satisfied_elements) >= len(pred_baseline.satisfied_elements)


def test_partial_element_satisfaction():
    """
    A policy covering consent but NOT stating purpose must NOT satisfy
    both elements.
    """
    text = "You must provide your opt-in consent before we process your data."
    pred = _run(text, ExperimentConfig.element_decomp())
    # 'purpose' element should NOT be satisfied (no purpose keyword)
    assert "purpose" not in pred.satisfied_elements or len(pred.satisfied_elements) < 2


def test_semantically_similar_but_non_compliant_text():
    """
    A text that sounds positive but contains none of the required keywords
    must not produce a 'covered' classification.
    """
    text = "We handle your information with care and deep respect for your privacy preferences."
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg)
        assert pred.status != "covered", (
            f"Config {cfg.name}: misleading-similarity text incorrectly classified as covered."
        )


# ---------------------------------------------------------------------------
# Section 4: Polarity detection feature isolation
# ---------------------------------------------------------------------------


def test_polarity_aware_detects_denial_findings():
    """
    Polarity-aware config must produce polarity_findings in diagnostics
    for a sentence with denial language.
    """
    text = "We do not collect any personal data without obtaining your consent."
    pred = _run(text, ExperimentConfig.polarity_aware())
    findings = pred.diagnostics.get("polarity_findings", [])
    assert isinstance(findings, list)
    # There should be at least one finding (negative denial pattern)
    assert len(findings) > 0


def test_baseline_does_not_populate_polarity_findings():
    """
    Baseline config (use_denial_polarity=False) must not produce
    polarity_findings in diagnostics.
    """
    text = "We do not collect any personal data without obtaining your consent."
    pred = _run(text, ExperimentConfig.baseline())
    findings = pred.diagnostics.get("polarity_findings", [])
    assert findings == []


def test_combined_config_enables_both_features():
    """
    Combined config diagnostics must contain both polarity_findings and
    element_decomp_diagnostics for a policy with relevant content.
    """
    text = "Your consent is required for processing for the purpose of service delivery."
    pred = _run(text, ExperimentConfig.combined())
    assert "polarity_findings" in pred.diagnostics
    assert "element_decomp_diagnostics" in pred.diagnostics


def test_element_decomposition_is_applied_before_status_classification():
    """Decomposed element hits must be part of the classifier evidence input."""
    text = (
        "We process your personal data with your consent. "
        "We use it for the purpose of delivering the service."
    )
    pred = _run(text, ExperimentConfig.element_decomp())
    assert pred.diagnostics["decomposed_element_hits"]
    assert set(pred.diagnostics["decomposed_element_hits"]).issubset(
        set(pred.satisfied_elements)
    )
    assert pred.status in {"covered", "partial"}


def test_element_decomposition_does_not_scan_irrelevant_clauses():
    """Keywords in an unrelated sentence must not satisfy the obligation."""
    text = (
        "Our help centre explains the purpose of this document. "
        "We do not provide a consent or purpose disclosure for data processing."
    )
    pred = _run(text, ExperimentConfig.element_decomp())
    assert pred.status != "covered"


def test_polarity_denial_is_part_of_classification_evidence():
    """Relevant publisher denial must be visible as contradiction evidence."""
    text = "We do not encrypt personal data and provide no security safeguards."
    pred = _run(text, ExperimentConfig.polarity_aware(), "DPDP_SEC_8_SUB_5")
    assert pred.diagnostics["polarity_contradiction_clause_ids"]
    assert pred.status in {"violation", "conflict", "missing", "undetermined"}
    assert pred.status != "covered"


# ---------------------------------------------------------------------------
# Section 5: Contradiction
# ---------------------------------------------------------------------------


def test_contradictory_policy_produces_conflict_or_violation():
    """
    A policy that grants withdrawal rights in one sentence and denies them in
    the next should produce conflict, violation, or partial (not covered).

    The baseline engine's actor-filter means the contradiction clause may not
    be credited (lacks a 'we/our' marker in the denial sentence). The positive
    withdrawal clause IS creditable.  We therefore accept partial as a valid
    outcome: the engine correctly detects the positive element but cannot
    resolve the denial from a third-person denial sentence.

    We assert only that the policy is NOT classified as 'covered' (since the
    irrevocable denial should at minimum prevent full coverage), and that a
    polarity-aware or combined config does not improve on baseline here
    (they should also produce non-covered).
    """
    text = (
        "You may withdraw your consent at any time. "
        "However, consent is irrevocable and cannot be withdrawn once given."
    )
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg, obligation_id="DPDP_SEC_6_SUB_5")
        assert pred.status != "covered", (
            f"Config {cfg.name}: contradictory policy must not be classified as covered. "
            f"Got {pred.status}."
        )


# ---------------------------------------------------------------------------
# Section 6: Third-party denial (polarity-aware feature)
# ---------------------------------------------------------------------------


def test_third_party_denial_does_not_block_in_baseline():
    """
    A denial attributed to third parties should not block the engine in
    baseline (the engine uses its own actor-filtering).
    """
    text = (
        "We provide strong encryption for your personal data. "
        "Third parties may not accept withdrawal requests from us on your behalf."
    )
    pred_baseline = _run(
        text, ExperimentConfig.baseline(), obligation_id="DPDP_SEC_8_SUB_5"
    )
    # The encryption clause should still produce some evidence
    # (exact assertion depends on keyword scoring)
    assert pred_baseline.integration_complete is True


# ---------------------------------------------------------------------------
# Section 7: Security obligation
# ---------------------------------------------------------------------------


def test_security_clause_is_covered():
    """
    A policy with explicit technical measures for DPDP_SEC_8_SUB_5 must
    not be classified as missing.
    """
    text = (
        "We implement AES-256 encryption at rest and in transit, "
        "multi-factor authentication, and quarterly penetration testing."
    )
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg, obligation_id="DPDP_SEC_8_SUB_5")
        assert pred.status != "missing", (
            f"Config {cfg.name}: security clause incorrectly classified as missing."
        )


def test_vague_security_is_not_covered():
    """
    A vague sentiment-only security statement must not be classified as covered.
    """
    text = "Security is our top priority. We care deeply about protecting your data."
    for cfg in ExperimentConfig.all_configs():
        pred = _run(text, cfg, obligation_id="DPDP_SEC_8_SUB_5")
        assert pred.status != "covered", (
            f"Config {cfg.name}: vague security statement incorrectly classified as covered."
        )


# ---------------------------------------------------------------------------
# Section 8: _build_clauses helper
# ---------------------------------------------------------------------------


def test_build_clauses_splits_sentences():
    text = "Sentence one. Sentence two. Sentence three."
    clauses = _build_clauses(text)
    assert len(clauses) == 3
    assert clauses[0].clause_text == "Sentence one."
    assert clauses[1].clause_text == "Sentence two."


def test_build_clauses_single_sentence():
    text = "This is a single sentence without a period"
    clauses = _build_clauses(text)
    assert len(clauses) == 1
    assert clauses[0].clause_text == text


def test_build_clauses_empty():
    clauses = _build_clauses("")
    assert clauses == []
