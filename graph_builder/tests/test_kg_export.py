from __future__ import annotations

import json
from pathlib import Path

import pytest

from graph_builder.graph_ir import GraphIR, GraphNode
from graph_builder.kg_export import graph_ir_to_kg_dict, main, write_kg_export

from tests.conftest import sample_graph_ir


def test_sample_ir_exports_section_and_obligation() -> None:
  payload = graph_ir_to_kg_dict(sample_graph_ir(), law_code="IT-ACT-2000")

  assert payload["law_code"] == "IT-ACT-2000"
  assert payload["language"] == "en"
  assert payload["sections"] == [
    {
      "section_id": "43A",
      "title": "Compensation for failure to protect data",
      "text": "Compensation for failure to protect data",
    }
  ]
  assert payload["obligations"] == [
    {
      "obligation_id": "obligation_protect",
      "section_id": "43A",
      "text": "Body corporate shall implement reasonable security practices",
    }
  ]


def test_law_code_falls_back_to_law_version_properties() -> None:
  payload = graph_ir_to_kg_dict(sample_graph_ir())
  assert payload["law_code"] == "Information Technology Act, 2000"


def test_obligation_text_joins_slots_when_text_missing() -> None:
  ir = GraphIR(
    nodes=[
      GraphNode(
        id="obl_1",
        label="Obligation",
        properties={
          "subject": "The Data Fiduciary",
          "action": "shall allow access",
          "object": "to personal data",
          "condition": "on request",
          "exception": "except legally withheld records",
        },
      )
    ]
  )
  payload = graph_ir_to_kg_dict(ir, law_code="DPDPA-2023")
  assert payload["obligations"][0]["text"] == (
    "The Data Fiduciary shall allow access to personal data on request "
    "except legally withheld records"
  )


def test_blank_obligation_text_is_skipped() -> None:
  ir = GraphIR(
    nodes=[
      GraphNode(id="obl_empty", label="Obligation", properties={"text": "  "}),
      GraphNode(id="sec_empty", label="Section", properties={"number": "S1", "title": ""}),
    ]
  )
  payload = graph_ir_to_kg_dict(ir, law_code="X")
  assert payload["obligations"] == []
  assert payload["sections"] == []


def test_write_kg_export_round_trips(tmp_path: Path) -> None:
  path = tmp_path / "IT-ACT-2000.json"
  write_kg_export(sample_graph_ir(), path, law_code="IT-ACT-2000")
  loaded = json.loads(path.read_text(encoding="utf-8"))
  assert loaded["law_code"] == "IT-ACT-2000"
  assert loaded["obligations"][0]["obligation_id"] == "obligation_protect"


def test_missing_law_code_raises() -> None:
  ir = GraphIR(nodes=[GraphNode(id="s", label="Section", properties={"title": "Scope", "text": "x"})])
  with pytest.raises(ValueError, match="law_code"):
    graph_ir_to_kg_dict(ir)


def test_cli_writes_output(tmp_path: Path) -> None:
  ir_path = tmp_path / "ir.json"
  out_path = tmp_path / "kg" / "IT-ACT-2000.json"
  ir_path.write_text(json.dumps(sample_graph_ir().to_dict()), encoding="utf-8")

  assert main([str(ir_path), "-o", str(out_path), "--law-code", "IT-ACT-2000"]) == 0
  loaded = json.loads(out_path.read_text(encoding="utf-8"))
  assert loaded["law_code"] == "IT-ACT-2000"
  assert len(loaded["obligations"]) == 1
