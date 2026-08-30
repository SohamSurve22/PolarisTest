"""Live dense (and graph) RAG eval. Writes rag_live_eval.json. Not used by /analyze."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
  str(ROOT / "rag" / "src"),
  str(ROOT / "vectorization" / "src"),
  str(ROOT / "compliance" / "src"),
  str(ROOT / "graph_builder" / "src"),
  str(ROOT / "document_pipeline" / "src"),
  str(ROOT / "policy_compare" / "src"),
]

from rag.bench import GOLD_PATH, load_gold, recall_hit
from rag.service import answer_question

MUST = {
  "dpdp_withdraw": ["withdraw"],
  "dpdp_withdraw_consequences": ["withdraw"],
  "dpdp_consent_free": ["consent"],
  "itact_43a": ["compensat"],
  "certin_6_hours": ["6 hour"],
  "spdi_grievance": ["grievance"],
  "spdi_withdraw": ["withdraw"],
  "dpdp_children_consent": ["consent"],
  "dpdp_children_tracking": ["track"],
  "dpdp_security": ["secur"],
  "dpdp_breach": ["breach"],
  "dpdp_purpose": ["purpose"],
}


def grounded(answer: str, qid: str, cited: list[str], gold_ids: list[str]) -> str:
  text = answer.lower()
  needles = MUST.get(qid, [])
  has_fact = any(n in text for n in needles)
  cites = any(gid.lower() in text.lower() for gid in gold_ids) or any(
    gid in cited for gid in gold_ids
  )
  refuse = "cannot tell" in text or "provided text" in text
  if has_fact and cites:
    return "grounded"
  if has_fact and recall_hit_ids(cited, gold_ids):
    return "grounded"
  if refuse and not has_fact:
    return "abstain"
  if has_fact:
    return "partial"
  return "off"


def recall_hit_ids(cited: list[str], gold_ids: list[str]) -> bool:
  return any(gid in cited for gid in gold_ids)


def main() -> None:
  gold = load_gold(GOLD_PATH)
  rows = []
  for mode in ("dense", "graph"):
    for item in gold["questions"]:
      result = answer_question(item["question"], mode=mode)
      cited = [c.id for c in result.citations]
      gold_ids = item["gold_dense_ids"] if mode == "dense" else item["gold_graph_ids"]
      hit = recall_hit(result.citations, gold_ids)
      grade = grounded(result.answer, item["id"], cited, gold_ids)
      row = {
        "id": item["id"],
        "mode": mode,
        "question": item["question"],
        "gold_ids": gold_ids,
        "cited": cited,
        "recall_hit": hit,
        "grounded": grade,
        "retrieve_ms": round(result.retrieve_ms, 1),
        "generate_ms": round(result.generate_ms, 1),
        "answer": result.answer[:800],
        "top_title": result.citations[0].title if result.citations else "",
        "top_score": round(result.citations[0].score, 3) if result.citations else 0.0,
      }
      print(
        f"{mode:5} {item['id']:28} hit={hit} {grade:8} "
        f"r={result.retrieve_ms:.0f}ms g={result.generate_ms:.0f}ms {cited[:3]}"
      )
      rows.append(row)

  out = ROOT / "rag_live_eval.json"
  out.write_text(json.dumps({"k": gold.get("k", 5), "rows": rows}, indent=2), encoding="utf-8")
  print("wrote", out)


if __name__ == "__main__":
  main()
