"""Promote selected Jev proposals into reviewed Qwen labels.

The review file is JSONL with ``pair_id``, ``status`` and optional ``reviewer``.
No proposal is promoted implicitly.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STATUSES = {
    "covered", "partial", "missing", "not_applicable", "undetermined",
    "conflict", "violation",
}


def review(proposals: Path, decisions: Path, output: Path) -> int:
    updates = {}
    for line_no, line in enumerate(decisions.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        pair_id = str(row.get("pair_id") or "")
        status = str(row.get("status") or "").lower()
        if not pair_id or status not in STATUSES:
            raise ValueError(f"{decisions}:{line_no}: pair_id and valid status are required")
        updates[pair_id] = {
            "status": status,
            "reviewer": str(row.get("reviewer") or ""),
        }

    updated = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with proposals.open(encoding="utf-8") as source, output.open("w", encoding="utf-8") as target:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            decision = updates.get(row.get("pair_id"))
            if decision is not None:
                row["status"] = decision["status"]
                row["review_status"] = "reviewed"
                row["reviewer"] = decision["reviewer"]
                row["reviewed_at"] = datetime.now(timezone.utc).isoformat()
                updated += 1
            target.write(json.dumps(row, ensure_ascii=False) + "\n")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("proposals", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(f"Reviewed {review(args.proposals, args.decisions, args.output)} proposal(s)")


if __name__ == "__main__":
    main()
