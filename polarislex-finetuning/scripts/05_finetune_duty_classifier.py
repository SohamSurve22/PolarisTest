"""Fine-tune Qwen2.5-3B on reviewed duty-classification pairs.

This is intentionally separate from the older policy-extraction trainer. It
refuses pending Jev proposals and trains only on rows marked ``reviewed``.
The benchmark gold files are never consumed by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

STATUSES = {
    "covered", "partial", "missing", "not_applicable", "undetermined",
    "conflict", "violation",
}


def load_reviewed(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("review_status") != "reviewed":
            continue
        status = row.get("status")
        if status not in STATUSES:
            raise ValueError(f"{path}:{line_no}: invalid reviewed status {status!r}")
        rows.append(row)
    if not rows:
        raise ValueError("No reviewed rows found; review Jev proposals before training")
    return rows


def to_chat_rows(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        prompt = {
            "duty": row["duty"],
            "policy_clauses": row["policy_clauses"],
            "allowed_statuses": sorted(STATUSES),
        }
        result.append({
            "pair_id": row["pair_id"],
            "messages": [
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                {"role": "assistant", "content": json.dumps({"status": row["status"]})},
            ],
        })
    return result


def train(input_path: Path, output_dir: Path, base_model: str, epochs: int) -> None:
    rows = load_reviewed(input_path)
    chat_rows = to_chat_rows(rows)

    # Heavy training dependencies are optional and imported only when training
    # is explicitly requested.
    import torch
    from datasets import Dataset
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=4096,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    def format_row(row: dict) -> dict:
        text = tokenizer.apply_chat_template(
            row["messages"], tokenize=False, add_generation_prompt=False
        )
        return {"text": text}

    dataset = Dataset.from_list(chat_rows).map(format_row)
    args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        num_train_epochs=epochs,
        learning_rate=2e-4,
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        logging_steps=10,
        save_strategy="epoch",
        report_to="none",
    )
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=4096,
        args=args,
        packing=False,
    )
    trainer.train()
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    manifest = {
        "base_model": base_model,
        "rows": len(rows),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "output_dir": str(output_dir),
    }
    (output_dir / "training_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def preflight(input_path: Path) -> dict[str, object]:
    """Report label/dependency readiness without importing training stacks."""
    required = ["torch", "datasets", "unsloth", "trl", "transformers", "peft", "bitsandbytes"]
    result: dict[str, object] = {
        "input": str(input_path),
        "input_exists": input_path.is_file(),
        "reviewed_rows": 0,
        "missing_dependencies": [name for name in required if importlib.util.find_spec(name) is None],
    }
    if input_path.is_file():
        try:
            result["reviewed_rows"] = len(load_reviewed(input_path))
        except (OSError, ValueError) as exc:
            result["label_error"] = str(exc)
    result["ready"] = bool(
        result["input_exists"]
        and result["reviewed_rows"]
        and not result["missing_dependencies"]
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Reviewed proposal JSONL")
    parser.add_argument("--output", type=Path, default=Path("adapters/polarislex-qwen2.5-3b-duty"))
    parser.add_argument("--base-model", default="unsloth/Qwen2.5-3B-Instruct-bnb-4bit")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Report reviewed-label and dependency readiness without training",
    )
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(preflight(args.input), indent=2))
        return
    train(args.input, args.output, args.base_model, args.epochs)


if __name__ == "__main__":
    main()
