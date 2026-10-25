"""Write the Ollama Modelfile for the trained duty classifier."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="qwen2.5:3b")
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("Modelfile.polarislex-duty"))
    parser.add_argument("--name", default="polarislex-qwen2.5-3b-duty")
    args = parser.parse_args()
    if not args.adapter.exists():
        raise SystemExit(f"Adapter directory does not exist: {args.adapter}")
    args.output.write_text(
        f"FROM {args.base}\nADAPTER {args.adapter.resolve()}\n"
        "SYSTEM You classify one legal duty against policy clauses. Return only JSON "
        "with status, clause_ids, reason, and confidence.\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}; run: ollama create {args.name} -f {args.output}")


if __name__ == "__main__":
    main()
