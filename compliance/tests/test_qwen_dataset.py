from compliance.qwen_dataset import reviewed_training_rows
import importlib.util
from pathlib import Path


def _review_module():
    path = Path(__file__).parents[2] / "polarislex-finetuning" / "scripts" / "review_qwen_proposals.py"
    spec = importlib.util.spec_from_file_location("review_qwen_proposals", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _row(review_status: str, status: str = "covered") -> dict:
    return {
        "pair_id": "policy:TINY_1",
        "duty": {"obligation_id": "TINY_1", "title": "Consent"},
        "policy_clauses": [{"clause_id": "C1", "text": "We obtain consent."}],
        "review_status": review_status,
        "status": status,
    }


def test_pending_jev_proposals_are_not_training_rows() -> None:
    assert reviewed_training_rows([_row("pending")]) == []


def test_reviewed_row_is_chat_training_pair() -> None:
    rows = reviewed_training_rows([_row("reviewed", "violation")])
    assert len(rows) == 1
    assert rows[0]["messages"][1]["content"] == '{"status": "violation"}'


def test_review_promoter_requires_explicit_decision(tmp_path: Path) -> None:
    module = _review_module()
    proposals = tmp_path / "proposals.jsonl"
    decisions = tmp_path / "decisions.jsonl"
    output = tmp_path / "reviewed.jsonl"
    proposals.write_text(
        '{"pair_id":"p1","review_status":"pending","status":""}\n'
        '{"pair_id":"p2","review_status":"pending","status":""}\n',
        encoding="utf-8",
    )
    decisions.write_text(
        '{"pair_id":"p1","status":"covered","reviewer":"legal"}\n',
        encoding="utf-8",
    )

    assert module.review(proposals, decisions, output) == 1
    rows = [__import__("json").loads(line) for line in output.read_text().splitlines()]
    assert rows[0]["review_status"] == "reviewed"
    assert rows[0]["reviewer"] == "legal"
    assert rows[1]["review_status"] == "pending"
