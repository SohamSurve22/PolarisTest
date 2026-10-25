# Evaluation metrics

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ConfusionMatrix:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else 0.0
    
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else 0.0
    
    def f1(self) -> float:
        p = self.precision()
        r = self.recall()
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.tn + self.fn
        return (self.tp + self.tn) / total if total > 0 else 0.0
    
    def false_covered_rate(self) -> float:
        denom = self.fp + self.tn
        return self.fp / denom if denom > 0 else 0.0
    
    def false_negative_rate(self) -> float:
        denom = self.tp + self.fn
        return self.fn / denom if denom > 0 else 0.0


@dataclass
class EvaluationMetrics:
    confusion_matrix: ConfusionMatrix
    element_precision: float = 0.0
    element_recall: float = 0.0
    element_f1: float = 0.0
    macro_f1: float = 0.0
    false_covered_count: int = 0
    false_covered_rate: float = 0.0
    false_negative_rate: float = 0.0
    coverage_uncertainty_rate: float = 0.0
    total_cases: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "confusion_matrix": {
                "tp": self.confusion_matrix.tp,
                "fp": self.confusion_matrix.fp,
                "tn": self.confusion_matrix.tn,
                "fn": self.confusion_matrix.fn
            },
            "precision": self.confusion_matrix.precision(),
            "recall": self.confusion_matrix.recall(),
            "f1": self.confusion_matrix.f1(),
            "accuracy": self.confusion_matrix.accuracy(),
            "element_precision": self.element_precision,
            "element_recall": self.element_recall,
            "element_f1": self.element_f1,
            "macro_f1": self.macro_f1,
            "false_covered_count": self.false_covered_count,
            "false_covered_rate": self.false_covered_rate,
            "false_negative_rate": self.false_negative_rate,
            "coverage_uncertainty_rate": self.coverage_uncertainty_rate,
            "total_cases": self.total_cases
        }


def compute_metrics(predictions: list[dict], gold: list[dict]) -> EvaluationMetrics:
    cm = ConfusionMatrix()
    element_tp = element_fp = element_fn = 0
    
    for pred, g in zip(predictions, gold):
        pred_status = pred.get("status", "missing")
        gold_status = g.get("expected_status", "missing")
        
        pred_covered = pred_status == "covered"
        gold_covered = gold_status == "covered"
        
        if pred_covered and gold_covered:
            cm.tp += 1
        elif pred_covered and not gold_covered:
            cm.fp += 1
        elif not pred_covered and gold_covered:
            cm.fn += 1
        else:
            cm.tn += 1
        
        pred_elements = pred.get("satisfied_elements", set())
        gold_elements = set(g.get("expected_elements", []))
        if isinstance(pred_elements, list):
            pred_elements = set(pred_elements)
        
        element_tp += len(pred_elements & gold_elements)
        element_fp += len(pred_elements - gold_elements)
        element_fn += len(gold_elements - pred_elements)
    
    elem_p = element_tp / (element_tp + element_fp) if (element_tp + element_fp) > 0 else 0.0
    elem_r = element_tp / (element_tp + element_fn) if (element_tp + element_fn) > 0 else 0.0
    elem_f1 = 2 * elem_p * elem_r / (elem_p + elem_r) if (elem_p + elem_r) > 0 else 0.0
    
    metrics = EvaluationMetrics(
        confusion_matrix=cm,
        element_precision=elem_p,
        element_recall=elem_r,
        element_f1=elem_f1,
        macro_f1=cm.f1(),
        false_covered_count=cm.fp,
        false_covered_rate=cm.false_covered_rate(),
        false_negative_rate=cm.false_negative_rate(),
        coverage_uncertainty_rate=0.0,
        total_cases=len(predictions)
    )
    return metrics
