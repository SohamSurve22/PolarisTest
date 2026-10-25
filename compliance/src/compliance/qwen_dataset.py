"""Build reviewed Jev/Qwen comparison pairs.

The Fortune 500 policy corpus is evidence, not a labelled training set. This
module writes Jev proposals with ``review_status=pending`` and only promotes
rows explicitly reviewed by a person into the training JSONL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.orchestrator import create_default_orchestrator

from compliance.graph_scope import ir_from_paths, obligation_nodes
from compliance.jev import JevClient
from compliance.duty_rules import load_duty_rules, resolve_duty_rule

_STATUSES = frozenset({
    "covered", "partial", "missing", "not_applicable", "undetermined",
    "conflict", "violation",
})


def _document(path: Path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    source = DocumentSource(
        metadata=DocumentMetadata(
            document_id=f"QWEN_{digest}",
            filename=path.name,
            format=DocumentFormat.TXT,
            source_path=str(path),
        )
    )
    return create_default_orchestrator().run(source).entity


def _clauses(document) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in document.entity_clauses:
        contextual = getattr(item, "contextual_clause", None)
        clause = getattr(getattr(contextual, "classified_clause", None), "clause", None)
        if clause is None or not (clause.clause_text or "").strip():
            continue
        rows.append({
            "clause_id": clause.clause_id,
            "section_title": clause.section_title,
            "text": clause.clause_text,
        })
    return rows


def build_proposals(
    policy_dir: Path,
    law_paths: Iterable[Path],
    *,
    holdout_paths: Iterable[Path] = (),
    client: JevClient | None = None,
) -> list[dict[str, object]]:
    """Create pending Jev-labelled pairs, excluding explicit holdouts."""
    holdouts = {path.resolve() for path in holdout_paths}
    duties = obligation_nodes(ir_from_paths(list(law_paths)))
    rules = load_duty_rules()
    jev = client or JevClient()
    rows: list[dict[str, object]] = []
    for policy_path in sorted(policy_dir.glob("*.txt")):
        if policy_path.resolve() in holdouts:
            continue
        clauses = _clauses(_document(policy_path))
        for duty in duties:
            props = duty.properties or {}
            rule = resolve_duty_rule(
                duty.id,
                rules=rules,
                catalog_roles=tuple(str(item) for item in (props.get("entity_ids") or [])),
            )
            answer = jev.classify_applicable_duty(
                obligation_id=duty.id,
                act=str(props.get("act") or ""),
                title=str(props.get("title") or duty.id),
                summary=str(props.get("summary") or ""),
                requirement_elements=[
                    {"id": element.id, "label": element.label}
                    for element in rule.requirement_elements
                ],
                policy_clauses=clauses,
            )
            status = str(answer.get("status") or "undetermined").lower()
            if status not in _STATUSES:
                status = "undetermined"
            rows.append({
                "pair_id": f"{policy_path.stem}:{duty.id}",
                "policy_file": str(policy_path),
                "duty": {
                    "obligation_id": duty.id,
                    "act": str(props.get("act") or ""),
                    "title": str(props.get("title") or duty.id),
                    "summary": str(props.get("summary") or ""),
                    "requirement_elements": [
                        {"id": element.id, "label": element.label}
                        for element in rule.requirement_elements
                    ],
                },
                "policy_clauses": clauses,
                "jev_proposal": {
                    "status": status,
                    "clause_ids": list(answer.get("clause_ids") or []),
                    "reason": str(answer.get("reason") or ""),
                    "confidence": float(answer.get("confidence") or 0.0),
                },
                "review_status": "pending",
                "status": "",
            })
    return rows


def write_proposals(rows: Iterable[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def reviewed_training_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    """Return only human-reviewed rows in chat fine-tuning format."""
    result = []
    for row in rows:
        if row.get("review_status") != "reviewed" or row.get("status") not in _STATUSES:
            continue
        duty = row["duty"]
        prompt = {
            "duty": duty,
            "policy_clauses": row["policy_clauses"],
            "allowed_statuses": sorted(_STATUSES),
        }
        result.append({
            "pair_id": row["pair_id"],
            "messages": [
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                {"role": "assistant", "content": json.dumps({"status": row["status"]}, ensure_ascii=False)},
            ],
        })
    return result


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy_dir", type=Path)
    parser.add_argument("--law", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--holdout", action="append", type=Path, default=[])
    args = parser.parse_args()
    rows = build_proposals(args.policy_dir, args.law, holdout_paths=args.holdout)
    write_proposals(rows, args.output)
    print(f"Wrote {len(rows)} pending Jev proposals to {args.output}")


if __name__ == "__main__":
    _main()
