"""
Metric tests with hand-calculated expected values.

Metric definitions (verified against metrics.py):
  Positive class: status == "covered"
  Negative class: everything else

  TP: predicted covered  AND gold covered
  FP: predicted covered  AND gold NOT covered  (false-covered)
  FN: predicted NOT covered AND gold covered
  TN: predicted NOT covered AND gold NOT covered

  Precision = TP / (TP + FP)
  Recall    = TP / (TP + FN)
  F1        = 2*P*R / (P+R)

  false_covered_count = FP
  false_covered_rate  = FP / (FP + TN)   [among truly NOT covered, fraction wrongly called covered]
  false_negative_rate = FN / (FN + TP)   [among truly covered, fraction wrongly called NOT covered]

  element_f1: micro-F1 over element satisfaction flags
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from research.metrics import ConfusionMatrix, EvaluationMetrics, compute_metrics


# ---------------------------------------------------------------------------
# Hand-calculated ConfusionMatrix tests
# ---------------------------------------------------------------------------


def test_confusion_matrix_basic():
    """tp=3 fp=1 tn=4 fn=2 — hand-verified values."""
    cm = ConfusionMatrix(tp=3, fp=1, tn=4, fn=2)

    # Precision = 3/(3+1) = 0.75
    assert abs(cm.precision() - 0.75) < 1e-9

    # Recall = 3/(3+2) = 0.60
    assert abs(cm.recall() - 0.60) < 1e-9

    # F1 = 2*0.75*0.60/(0.75+0.60) = 0.9/1.35 = 2/3 ≈ 0.6667
    assert abs(cm.f1() - (2 / 3)) < 1e-9

    # Accuracy = (3+4)/10 = 0.70
    assert abs(cm.accuracy() - 0.70) < 1e-9

    # false_covered_rate = FP/(FP+TN) = 1/5 = 0.20
    assert abs(cm.false_covered_rate() - 0.20) < 1e-9

    # false_negative_rate = FN/(FN+TP) = 2/5 = 0.40
    assert abs(cm.false_negative_rate() - 0.40) < 1e-9


def test_confusion_matrix_all_tp():
    """Perfect classifier — all true positives."""
    cm = ConfusionMatrix(tp=5, fp=0, tn=0, fn=0)
    assert cm.precision() == 1.0
    assert cm.recall() == 1.0
    assert cm.f1() == 1.0
    assert cm.false_covered_rate() == 0.0  # FP/(FP+TN) = 0/(0+0) → 0.0
    assert cm.false_negative_rate() == 0.0


def test_confusion_matrix_all_tn():
    """All true negatives (never predicts covered, nothing should be covered)."""
    cm = ConfusionMatrix(tp=0, fp=0, tn=5, fn=0)
    assert cm.precision() == 0.0   # undefined → 0.0
    assert cm.recall() == 0.0      # undefined → 0.0
    assert cm.f1() == 0.0
    assert cm.false_covered_rate() == 0.0  # FP/(FP+TN) = 0/5 = 0.0


def test_confusion_matrix_all_fn():
    """All false negatives (always predicts not-covered but all are covered)."""
    cm = ConfusionMatrix(tp=0, fp=0, tn=0, fn=4)
    assert cm.precision() == 0.0
    assert cm.recall() == 0.0      # 0/(0+4)
    assert cm.false_negative_rate() == 1.0   # 4/(4+0)


def test_confusion_matrix_all_fp():
    """All false positives (always predicts covered but none are covered)."""
    cm = ConfusionMatrix(tp=0, fp=3, tn=0, fn=0)
    assert cm.precision() == 0.0  # 0/(0+3)
    assert cm.false_covered_rate() == 1.0  # 3/(3+0)
    assert cm.false_negative_rate() == 0.0  # FN/(FN+TP) = 0/0 → 0.0


def test_confusion_matrix_mixed():
    """Matches the existing test_confusion_matrix test."""
    cm = ConfusionMatrix(tp=10, fp=2, tn=5, fn=3)
    assert abs(cm.precision() - 10 / 12) < 0.001
    assert abs(cm.recall() - 10 / 13) < 0.001
    assert abs(cm.false_covered_rate() - 2 / 7) < 0.001
    assert abs(cm.false_negative_rate() - 3 / 13) < 0.001


# ---------------------------------------------------------------------------
# Hand-calculated compute_metrics tests
# ---------------------------------------------------------------------------


def test_compute_metrics_perfect():
    """3 cases, all correctly predicted covered."""
    preds = [
        {"status": "covered", "satisfied_elements": ["e1"]},
        {"status": "covered", "satisfied_elements": ["e2"]},
        {"status": "covered", "satisfied_elements": ["e1", "e2"]},
    ]
    gold = [
        {"expected_status": "covered", "expected_elements": ["e1"]},
        {"expected_status": "covered", "expected_elements": ["e2"]},
        {"expected_status": "covered", "expected_elements": ["e1", "e2"]},
    ]
    m = compute_metrics(preds, gold)
    assert m.confusion_matrix.tp == 3
    assert m.confusion_matrix.fp == 0
    assert m.confusion_matrix.fn == 0
    assert m.confusion_matrix.tn == 0
    assert abs(m.confusion_matrix.precision() - 1.0) < 1e-9
    assert abs(m.confusion_matrix.recall() - 1.0) < 1e-9
    assert abs(m.element_f1 - 1.0) < 1e-9


def test_compute_metrics_no_true_positives():
    """2 truly covered cases both predicted missing."""
    preds = [
        {"status": "missing", "satisfied_elements": []},
        {"status": "missing", "satisfied_elements": []},
    ]
    gold = [
        {"expected_status": "covered", "expected_elements": ["e1"]},
        {"expected_status": "covered", "expected_elements": ["e2"]},
    ]
    m = compute_metrics(preds, gold)
    assert m.confusion_matrix.tp == 0
    assert m.confusion_matrix.fn == 2
    assert m.confusion_matrix.fp == 0
    assert m.confusion_matrix.tn == 0
    assert m.confusion_matrix.precision() == 0.0
    assert m.confusion_matrix.recall() == 0.0
    assert m.false_covered_count == 0
    assert m.false_covered_rate == 0.0


def test_compute_metrics_false_covered():
    """
    1 TP, 1 FP, 1 FN, 1 TN — hand-verified matrix.

    Case 1: pred=covered, gold=covered  → TP
    Case 2: pred=covered, gold=missing  → FP (false-covered)
    Case 3: pred=missing,  gold=covered → FN
    Case 4: pred=missing,  gold=missing → TN
    """
    preds = [
        {"status": "covered", "satisfied_elements": ["e1"]},
        {"status": "covered", "satisfied_elements": []},
        {"status": "missing",  "satisfied_elements": []},
        {"status": "missing",  "satisfied_elements": []},
    ]
    gold = [
        {"expected_status": "covered", "expected_elements": ["e1"]},
        {"expected_status": "missing",  "expected_elements": []},
        {"expected_status": "covered",  "expected_elements": ["e2"]},
        {"expected_status": "missing",  "expected_elements": []},
    ]
    m = compute_metrics(preds, gold)
    assert m.confusion_matrix.tp == 1
    assert m.confusion_matrix.fp == 1
    assert m.confusion_matrix.fn == 1
    assert m.confusion_matrix.tn == 1
    # false_covered_count = FP = 1
    assert m.false_covered_count == 1
    # false_covered_rate = FP/(FP+TN) = 1/(1+1) = 0.5
    assert abs(m.false_covered_rate - 0.5) < 1e-9
    # false_negative_rate = FN/(FN+TP) = 1/(1+1) = 0.5
    assert abs(m.false_negative_rate - 0.5) < 1e-9
    # Precision = 1/(1+1) = 0.5
    assert abs(m.confusion_matrix.precision() - 0.5) < 1e-9
    # Recall = 1/(1+1) = 0.5
    assert abs(m.confusion_matrix.recall() - 0.5) < 1e-9
    # F1 = 2*0.5*0.5/(0.5+0.5) = 0.5
    assert abs(m.confusion_matrix.f1() - 0.5) < 1e-9


def test_compute_metrics_partial_counted_as_not_covered():
    """
    partial/missing/undetermined predictions all count as NOT covered
    (binary label: covered vs. everything-else).
    """
    preds = [
        {"status": "partial",      "satisfied_elements": ["e1"]},
        {"status": "undetermined", "satisfied_elements": []},
        {"status": "missing",      "satisfied_elements": []},
    ]
    gold = [
        {"expected_status": "covered", "expected_elements": ["e1"]},
        {"expected_status": "covered", "expected_elements": []},
        {"expected_status": "missing", "expected_elements": []},
    ]
    m = compute_metrics(preds, gold)
    # pred[0]: partial ≠ covered, gold=covered → FN
    # pred[1]: undetermined ≠ covered, gold=covered → FN
    # pred[2]: missing, gold=missing → TN
    assert m.confusion_matrix.fn == 2
    assert m.confusion_matrix.tn == 1
    assert m.confusion_matrix.tp == 0
    assert m.confusion_matrix.fp == 0


def test_compute_metrics_element_precision_recall():
    """
    Hand-calculated element micro-F1.

    pred elem: {e1, e3}   gold elem: {e1, e2}
    → TP=1, FP=1 (e3), FN=1 (e2)
    elem_precision = 1/2 = 0.5
    elem_recall    = 1/2 = 0.5
    elem_f1        = 0.5
    """
    preds = [{"status": "covered", "satisfied_elements": ["e1", "e3"]}]
    gold =  [{"expected_status": "covered", "expected_elements": ["e1", "e2"]}]
    m = compute_metrics(preds, gold)
    assert abs(m.element_precision - 0.5) < 1e-9
    assert abs(m.element_recall - 0.5) < 1e-9
    assert abs(m.element_f1 - 0.5) < 1e-9


def test_compute_metrics_empty_predictions():
    """Empty predictions list must not raise."""
    m = compute_metrics([], [])
    assert m.total_cases == 0
    assert m.confusion_matrix.tp == 0


def test_compute_metrics_undefined_metrics_no_crash():
    """
    When TP+FP=0 (precision undefined) and TP+FN=0 (recall undefined),
    both must return 0.0 without ZeroDivisionError.
    """
    cm = ConfusionMatrix(tp=0, fp=0, tn=3, fn=0)
    assert cm.precision() == 0.0
    assert cm.recall() == 0.0
    assert cm.f1() == 0.0
    assert cm.false_covered_rate() == 0.0


def test_to_dict_contains_all_keys():
    """EvaluationMetrics.to_dict() must contain every documented field."""
    preds = [{"status": "covered", "satisfied_elements": ["e1"]}]
    gold  = [{"expected_status": "covered", "expected_elements": ["e1"]}]
    m = compute_metrics(preds, gold)
    d = m.to_dict()
    required_keys = {
        "confusion_matrix", "precision", "recall", "f1", "accuracy",
        "element_precision", "element_recall", "element_f1", "macro_f1",
        "false_covered_count", "false_covered_rate", "false_negative_rate",
        "coverage_uncertainty_rate", "total_cases",
    }
    missing = required_keys - set(d.keys())
    assert not missing, f"to_dict() is missing keys: {missing}"


def test_false_covered_rate_denominator():
    """
    false_covered_rate denominator is (FP + TN), i.e. all truly-not-covered cases.
    This test validates the denominator explicitly.

    Setup: 3 truly-not-covered cases (FP+TN=3), 2 wrongly called covered (FP=2).
    false_covered_rate = 2/3 ≈ 0.6667
    """
    preds = [
        {"status": "covered", "satisfied_elements": []},  # FP
        {"status": "covered", "satisfied_elements": []},  # FP
        {"status": "missing",  "satisfied_elements": []},  # TN
    ]
    gold = [
        {"expected_status": "missing",  "expected_elements": []},
        {"expected_status": "missing",  "expected_elements": []},
        {"expected_status": "missing",  "expected_elements": []},
    ]
    m = compute_metrics(preds, gold)
    assert m.confusion_matrix.fp == 2
    assert m.confusion_matrix.tn == 1
    assert abs(m.false_covered_rate - 2 / 3) < 1e-9


def test_label_mapping_partial_is_binary_not_covered():
    """
    Gold status 'partial' must be treated as NOT covered in the binary label.
    A prediction of 'covered' against gold 'partial' must count as FP,
    NOT as TP.
    """
    preds = [{"status": "covered", "satisfied_elements": []}]
    gold  = [{"expected_status": "partial", "expected_elements": []}]
    m = compute_metrics(preds, gold)
    assert m.confusion_matrix.tp == 0
    assert m.confusion_matrix.fp == 1, (
        "partial gold should be treated as NOT covered (binary label) → FP"
    )


def test_label_mapping_violation_is_binary_not_covered():
    """Gold status 'violation' must count as NOT covered."""
    preds = [{"status": "covered", "satisfied_elements": []}]
    gold  = [{"expected_status": "violation", "expected_elements": []}]
    m = compute_metrics(preds, gold)
    assert m.confusion_matrix.fp == 1


def test_macro_f1_equals_binary_f1_for_single_class():
    """
    For the current single-class binary implementation, macro_f1 must
    equal the binary F1 of the confusion matrix.
    """
    preds = [
        {"status": "covered", "satisfied_elements": []},
        {"status": "missing", "satisfied_elements": []},
    ]
    gold = [
        {"expected_status": "covered", "expected_elements": []},
        {"expected_status": "missing", "expected_elements": []},
    ]
    m = compute_metrics(preds, gold)
    assert abs(m.macro_f1 - m.confusion_matrix.f1()) < 1e-9
