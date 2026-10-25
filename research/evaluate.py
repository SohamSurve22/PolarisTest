#!/usr/bin/env python3
"""
Research evaluation harness for PolarisLex.

Each configuration (A/B/C/D) is run through the actual compliance engine
via research.pipeline_adapter.  See that module for integration-completeness
caveats.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import subprocess

sys.path.insert(0, str(Path(__file__).parent / "src"))

from research.config import ExperimentConfig
from research.metrics import compute_metrics
from research.pipeline_adapter import run_case


def get_git_commit():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parent.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.decode().strip()
    except Exception:
        return "unknown"


def load_dataset(dataset_path: Path, split: str = "test"):
    cases = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                case = json.loads(line)
                if case.get("split") == split:
                    cases.append(case)
    return cases


def run_evaluation(dataset_path: str, split: str = "test", configs: list = None):
    if configs is None:
        configs = ExperimentConfig.all_configs()

    dataset_path = Path(dataset_path)
    cases = load_dataset(dataset_path, split)

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_manifest = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "git_commit": get_git_commit(),
        "dataset_path": str(dataset_path),
        "split": split,
        "num_cases": len(cases),
        "configs": [c.name for c in configs],
        "pipeline_integration": "keyword-stub (no Qdrant)",
    }

    all_results = {}

    for config in configs:
        print(f"\nRunning config {config.name}: {config.description}")
        predictions = []
        errors = []
        integration_failures = 0

        for case in cases:
            try:
                pred = run_case(case, config)
                predictions.append(pred.to_dict())
                if not pred.integration_complete:
                    integration_failures += 1
                print(
                    f"  {case['case_id']}: {pred.status}  "
                    f"elements={pred.satisfied_elements}  "
                    f"evidence_q={pred.diagnostics.get('evidence_quality', '?')}"
                )
            except Exception as e:
                import traceback
                err = {
                    "case_id": case.get("case_id"),
                    "config": config.name,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
                errors.append(err)
                print(f"  {case.get('case_id')}: ERROR — {e}")

        metrics = compute_metrics(predictions, cases)
        metrics_dict = metrics.to_dict()
        metrics_dict["integration_failures"] = integration_failures
        all_results[config.name] = metrics_dict

        pred_file = results_dir / f"predictions_{config.name}_{run_id}.jsonl"
        with open(pred_file, "w", encoding="utf-8") as f:
            for p in predictions:
                f.write(json.dumps(p) + "\n")

        if errors:
            err_file = results_dir / f"errors_{config.name}_{run_id}.jsonl"
            with open(err_file, "w", encoding="utf-8") as f:
                for e in errors:
                    f.write(json.dumps(e) + "\n")

    with open(results_dir / f"metrics_{run_id}.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    with open(results_dir / f"run_manifest_{run_id}.json", "w", encoding="utf-8") as f:
        json.dump(run_manifest, f, indent=2)

    report = generate_report(all_results, run_manifest, cases)
    with open(results_dir / f"REPORT_{run_id}.md", "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nResults saved to {results_dir}")
    print(f"Run ID: {run_id}")

    return all_results


def generate_report(results, manifest, cases=None):
    gold_dist: dict[str, int] = {}
    if cases:
        for c in cases:
            s = c.get("expected_status", "unknown")
            gold_dist[s] = gold_dist.get(s, 0) + 1

    report = "# Evaluation Report\n\n"
    report += f"**Run ID:** {manifest['run_id']}\n"
    report += f"**Timestamp:** {manifest['timestamp']}\n"
    report += f"**Git Commit:** {manifest['git_commit']}\n"
    report += f"**Dataset:** {manifest['dataset_path']} ({manifest['split']})\n"
    report += f"**Cases:** {manifest['num_cases']}\n"
    report += f"**Pipeline integration:** {manifest.get('pipeline_integration', 'unknown')}\n\n"

    if gold_dist:
        report += "## Label Distribution\n\n"
        report += "| Status | Count |\n|--------|-------|\n"
        for status, cnt in sorted(gold_dist.items()):
            report += f"| {status} | {cnt} |\n"
        report += "\n"

    report += "## Results\n\n"
    report += (
        "| Config | Precision | Recall | F1 | False-Covered Rate | "
        "False-Covered Count | Element F1 | Integration Failures |\n"
    )
    report += (
        "|--------|-----------|--------|-----|-------------------|"
        "-------------------|------------|----------------------|\n"
    )

    for name, metrics in results.items():
        report += (
            f"| {name} | {metrics['precision']:.3f} | {metrics['recall']:.3f} | "
            f"{metrics['f1']:.3f} | {metrics['false_covered_rate']:.3f} | "
            f"{metrics['false_covered_count']} | {metrics['element_f1']:.3f} | "
            f"{metrics.get('integration_failures', 0)} |\n"
        )

    report += "\n## Metric Definitions\n\n"
    report += (
        "- **Positive class**: `covered` (obligation is fully addressed in the policy).\n"
        "- **Negative class**: anything that is not `covered` "
        "(`partial`, `missing`, `undetermined`, `violation`, `conflict`).\n"
        "- **Precision**: TP / (TP + FP)  — of all obligations predicted covered, "
        "fraction actually covered.\n"
        "- **Recall**: TP / (TP + FN)  — of all obligations that are truly covered, "
        "fraction predicted covered.\n"
        "- **False-covered count** (FP): obligations predicted covered but actually not.\n"
        "- **False-covered rate**: FP / (FP + TN)  — among truly-not-covered obligations, "
        "fraction wrongly predicted covered.  Denominator is all true negatives + false "
        "positives.  This is the specificity complement (1 − specificity).\n"
        "- **False-negative rate**: FN / (FN + TP)  — among truly covered obligations, "
        "fraction wrongly predicted non-covered.\n"
        "- **Element F1**: micro-F1 over requirement-element satisfaction flags.\n"
    )

    report += "\n## Integration Notes\n\n"
    report += (
        "- Retrieval uses a keyword-overlap stub search, NOT Qdrant vector similarity.\n"
        "- Results cannot be compared directly to production analysis output.\n"
        "- Blocker for full integration: Qdrant service availability and populated "
        "kg_obligation collection.  See IMPLEMENTATION_AUDIT.md §5.\n"
        "- Jev/Ollama second-opinion path is skipped; it is advisory-only and does "
        "not affect the primary `.status` field.\n"
    )

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run research evaluation")
    parser.add_argument("--dataset", required=True, help="Path to dataset JSONL")
    parser.add_argument("--split", default="test", help="Split to evaluate")
    args = parser.parse_args()

    run_evaluation(args.dataset, args.split)
