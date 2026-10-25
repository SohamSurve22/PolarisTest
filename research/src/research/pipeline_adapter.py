"""
research.pipeline_adapter
=========================

Minimal adapter between the research evaluation harness and the actual
PolarisLex compliance engine.

Design principles
-----------------
* Reuses `compliance.matching.gather_evidence` and
  `compliance.classify.classify_duty` directly — no copy.
* Does NOT call Qdrant / Ollama.  Retrieval is performed via keyword
  scoring against the case's own `policy_text` clauses, exactly as the
  existing unit tests in compliance/tests/test_matching.py do.
* Feature flags (use_element_decomposition, use_denial_polarity) are
  applied *around* the genuine engine calls, not instead of them.
* Returns a structured PredictionResult that evaluate.py can serialise.

Blocker disclosure
------------------
The production path in `compliance.service.analyze_document` calls:
  1. `ir_from_paths` – requires pre-built GraphIR JSON law files on disk.
  2. `collect_credits` – calls Qdrant via `vectorization.pipeline.search_text`.
  3. `_jev_block` – calls the Jev/Ollama model.

This adapter bypasses (1) by loading the DutyRule directly from
duty_rules.json, bypasses (2) by using a keyword stub search built from
the case's own `policy_text`, and silently skips (3) (Jev is advisory
only and never sets `.status`).

This is NOT equivalent to running the full production pipeline.
Specifically, the stub search does not use semantic vector similarity
from Qdrant.  All cases where coverage depends on a high semantic score
(not keyword overlap) will therefore be under-scored relative to
production.  This limitation is documented in IMPLEMENTATION_AUDIT.md.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Compliance-engine imports (no services required)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "compliance" / "src"))

from compliance.classify import classify_duty
from compliance.duty_rules import load_duty_rules, resolve_duty_rule
from compliance.matching import gather_evidence, clause_has_denial_polarity, PARTIAL_SCORE

# ---------------------------------------------------------------------------
# Document-pipeline imports (models only)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "document_pipeline" / "src"))

from document_pipeline.models.clause import Clause
from document_pipeline.models.metadata import DocumentFormat, Span

# ---------------------------------------------------------------------------
# Research modules
# ---------------------------------------------------------------------------
from research.config import ExperimentConfig
from research.element_decomposition import (
    AtomicElement,
    DecomposedObligation,
    ElementDecomposer,
)
from research.polarity_detection import DenialPolarityDetector, Polarity

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DUTY_RULES = None  # loaded lazily

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset({
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in",
    "into", "is", "it", "of", "on", "or", "so", "that", "the", "this",
    "to", "we", "with",
})

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class PredictionResult:
    """Structured output of one adapter call."""

    case_id: str
    config: str
    status: str                              # ObligationStatus value
    satisfied_elements: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    integration_complete: bool = True        # False when a blocker was hit

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "config": self.config,
            "status": self.status,
            "satisfied_elements": self.satisfied_elements,
            "evidence": [e for e in self.evidence],
            "diagnostics": self.diagnostics,
            "integration_complete": self.integration_complete,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _duty_rules():
    global _DUTY_RULES
    if _DUTY_RULES is None:
        _DUTY_RULES = load_duty_rules()
    return _DUTY_RULES


def _text_tokens(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if len(w) >= 3 and w not in _STOP}


def _build_clauses(policy_text: str, document_id: str = "DOC_research") -> list[Clause]:
    """
    Split ``policy_text`` into sentence-level Clauses.

    Uses the same sentence-splitting regex as compliance.matching so the
    stub search and the real engine are consistent.
    """
    sentence_re = re.compile(r"(?<=[.!?])\s+")
    sentences = [s.strip() for s in sentence_re.split(policy_text.strip()) if s.strip()]
    if not sentences:
        sentences = [policy_text.strip()]

    clauses: list[Clause] = []
    for i, sent in enumerate(sentences):
        if not sent:
            continue
        cid = f"S001_C{i+1:03d}"
        clauses.append(
            Clause(
                clause_id=cid,
                section_id="S001",
                section_title="Policy Text",
                document_id=document_id,
                document_type=DocumentFormat.TXT,
                clause_text=sent,
                span=Span(start=0, end=len(sent)),
            )
        )
    return clauses


def _stub_search_fn(
    clauses: list[Clause],
    obligation_id: str,
    rule,
    *,
    use_denial_polarity: bool,
):
    """
    Return a search function that scores each clause against
    ``obligation_id`` using keyword overlap with the duty rule's
    requirement elements.

    If ``use_denial_polarity`` is True the polarity-aware research module
    filters out clauses with a blocking denial before they can accumulate
    score.  When False, polarity filtering is left entirely to the
    compliance engine's own ``clause_has_denial_polarity`` (baseline
    behaviour).
    """
    # Build keyword set from the rule's requirement_elements AND contradiction cues.
    # Contradiction cues must also get credits so gather_evidence can detect them.
    keyword_sets: list[set[str]] = []
    for spec in rule.requirement_elements:
        keyword_sets.append({kw.lower() for kw in spec.keywords if kw})
    all_keywords: set[str] = set().union(*keyword_sets) if keyword_sets else set()

    # Contradiction-cue keywords (tokenised) for scoring denial clauses.
    cue_keywords: set[str] = set()
    for cue in rule.contradiction_cues:
        cue_keywords.update(_text_tokens(cue))

    polarity_detector = DenialPolarityDetector() if use_denial_polarity else None

    def _score_clause(clause_text: str) -> float:
        """Keyword overlap score in [0, 1]."""
        all_kw = all_keywords | cue_keywords
        if not all_kw:
            return 0.0
        hits = sum(1 for kw in all_kw if kw in clause_text.lower())
        return min(hits / len(all_kw), 1.0)

    def search(query: str):
        """
        Stub SearchHit list for the given query.

        The query text is not used — we score every clause from the
        policy directly.  This mirrors what Qdrant would do for a
        closely-matching policy, but without vector similarity.
        """
        from vectorization.models import SearchHit

        results = []
        for clause in clauses:
            text = clause.clause_text

            # Polarity-aware pre-filter (research feature B/D only)
            if polarity_detector is not None:
                findings = polarity_detector.detect(text, obligation_id)
                if polarity_detector.has_blocking_denial(findings):
                    continue

            score = _score_clause(text)
            if score >= PARTIAL_SCORE:
                results.append(
                    SearchHit(
                        score=score,
                        source_type="kg_obligation",
                        payload={
                            "obligation_id": obligation_id,
                            "law_code": "DPDP",
                        },
                    )
                )
        return results

    return search


def _build_element_decomposer(obligation_id: str, rule) -> ElementDecomposer:
    """
    Build an ElementDecomposer whose decomposition mirrors the DutyRule's
    requirement_elements.  This is the research adapter that surfaces the
    rule structure as explicit AtomicElements — it does not alter keywords.
    """
    decomposer = ElementDecomposer()
    elements = [
        AtomicElement(
            element_id=spec.id,
            parent_obligation_id=obligation_id,
            description=spec.label,
            keywords=list(spec.keywords),
        )
        for spec in rule.requirement_elements
    ]
    if elements:
        decomp = DecomposedObligation(
            obligation_id=obligation_id,
            source_document="duty_rules.json",
            source_section=obligation_id,
            supporting_legal_text="",
            elements=elements,
        )
        decomposer.register_decomposition(decomp)
    return decomposer


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_case(case: dict[str, Any], config: ExperimentConfig) -> PredictionResult:
    """
    Run a single evaluation case through the real compliance engine.

    Steps
    -----
    1. Resolve the DutyRule for the case's obligation_id.
    2. Split policy_text into Clause objects.
    3. Build a stub search function (optionally polarity-filtered).
    4. Call gather_evidence from compliance.matching.
    5. Call classify_duty from compliance.classify.
    6. If use_element_decomposition: additionally assess elements via
       the research ElementDecomposer (uses same keywords as DutyRule).
    7. Package results into PredictionResult.
    """
    case_id = case.get("case_id", "unknown")
    obligation_id = case.get("obligation_id", "")
    policy_text = case.get("policy_text", "")
    cfg = config.baseline

    # 1. Resolve rule
    rules = _duty_rules()
    rule = resolve_duty_rule(obligation_id, rules=rules)

    # 2. Build clauses
    clauses = _build_clauses(policy_text, document_id=f"DOC_{case_id}")
    if not clauses:
        return PredictionResult(
            case_id=case_id,
            config=config.name,
            status="missing",
            diagnostics={"reason": "empty policy_text"},
        )

    # 3. Stub search (polarity-aware if configured)
    search_fn = _stub_search_fn(
        clauses,
        obligation_id,
        rule,
        use_denial_polarity=cfg.use_denial_polarity,
    )

    # 4. Collect credits (per the production pattern used in service.py)
    from compliance.matching import collect_credits
    try:
        credited = collect_credits(clauses, search_fn, {obligation_id})
        credited_for_oblig = credited.get(obligation_id, [])
    except Exception as exc:
        return PredictionResult(
            case_id=case_id,
            config=config.name,
            status="missing",
            diagnostics={"error": f"collect_credits failed: {exc}"},
            integration_complete=False,
        )

    # 5. Gather evidence
    try:
        evidence_bundle = gather_evidence(
            obligation_id,
            _obligation_title(obligation_id, rule),
            rule,
            clauses,
            credited_for_oblig,
        )
    except Exception as exc:
        return PredictionResult(
            case_id=case_id,
            config=config.name,
            status="missing",
            diagnostics={"error": f"gather_evidence failed: {exc}"},
            integration_complete=False,
        )

    # 6. Apply research features to the evidence bundle before classification.
    # This is intentionally after the genuine evidence collector and before the
    # genuine classifier: the feature flags must be able to affect status, not
    # merely add diagnostics after a status has already been chosen.
    satisfied_elements: list[str] = list(evidence_bundle.element_hits)
    elem_diagnostics: dict[str, Any] = {}
    decomposed_element_hits: set[str] = set()

    if cfg.use_element_decomposition and rule.requirement_elements:
        decomposer = _build_element_decomposer(obligation_id, rule)
        # Restrict decomposition to evidence already admitted by the engine.
        # Scanning the whole policy would turn irrelevant keyword mentions into
        # satisfied legal requirements.
        evidence_texts = list(evidence_bundle.expanded_texts)
        decomposed_element_hits, elem_diagnostics = decomposer.assess_elements(
            obligation_id,
            evidence_texts,
        )
        # Preserve engine hits and add only atomic elements confirmed in the
        # same evidence pool.  classify_duty reads element_hits when deciding
        # covered versus partial.
        merged = set(satisfied_elements) | decomposed_element_hits
        satisfied_elements = sorted(merged)
        evidence_bundle.element_hits = satisfied_elements

    # 7. Polarity-aware contradiction integration.
    polarity_diag: list[dict[str, Any]] = []
    polarity_contradiction_ids: list[str] = []
    if cfg.use_denial_polarity:
        detector = DenialPolarityDetector()
        for clause in clauses:
            findings = detector.detect(clause.clause_text, obligation_id)
            for f in findings:
                polarity_diag.append({
                    "text_span": f.text_span,
                    "polarity": f.polarity.value,
                    "confidence": f.confidence,
                    "reason": f.reason,
                    "is_third_party": f.is_third_party,
                })

            # A negative finding is only relevant when the clause mentions the
            # obligation vocabulary.  This prevents unrelated "we do not ..."
            # statements elsewhere in a policy from becoming violations.
            relevant_terms = [
                keyword.lower()
                for spec in rule.requirement_elements
                for keyword in spec.keywords
                if keyword
            ] + [cue.lower() for cue in rule.contradiction_cues if cue]
            relevant = any(term in clause.clause_text.lower() for term in relevant_terms)
            if relevant and detector.has_blocking_denial(findings):
                if clause.clause_id not in {
                    item.clause_id for item in evidence_bundle.contradiction_clauses
                }:
                    evidence_bundle.contradiction_clauses.append(clause)
                polarity_contradiction_ids.append(clause.clause_id)

    # 8. Classify only after decomposition/polarity have updated evidence.
    try:
        status, confidence, element_findings = classify_duty(
            applicable=True,
            evidence=evidence_bundle,
            rule=rule,
        )
    except Exception as exc:
        return PredictionResult(
            case_id=case_id,
            config=config.name,
            status="missing",
            diagnostics={"error": f"classify_duty failed: {exc}"},
            integration_complete=False,
        )

    matched_evidence = [
        {"clause_id": mc.clause_id, "section_title": mc.section_title, "text": mc.text}
        for mc in evidence_bundle.matched_clauses
    ]
    counter_evidence = [
        {"clause_id": c.clause_id, "text": c.clause_text}
        for c in evidence_bundle.contradiction_clauses
    ]

    return PredictionResult(
        case_id=case_id,
        config=config.name,
        status=str(status),
        satisfied_elements=satisfied_elements,
        evidence=matched_evidence,
        diagnostics={
            "config": config.name,
            "obligation_id": obligation_id,
            "evidence_quality": evidence_bundle.quality,
            "evidence_score": round(evidence_bundle.score, 4),
            "confidence": round(confidence, 4),
            "element_hits": list(evidence_bundle.element_hits),
            "generic_only": evidence_bundle.generic_only,
            "has_credited_support": evidence_bundle.has_credited_support,
            "counter_evidence": counter_evidence,
            "element_decomp_diagnostics": elem_diagnostics,
            "decomposed_element_hits": sorted(decomposed_element_hits),
            "polarity_findings": polarity_diag,
            "polarity_contradiction_clause_ids": sorted(set(polarity_contradiction_ids)),
            "use_element_decomposition": cfg.use_element_decomposition,
            "use_denial_polarity": cfg.use_denial_polarity,
        },
        integration_complete=True,
    )


def _obligation_title(obligation_id: str, rule) -> str:
    """Best-effort human title for the obligation (used by gather_evidence)."""
    # Derive a readable name from the obligation id
    return obligation_id.replace("_", " ").replace("SUB", "sub").replace("SEC", "Section")
