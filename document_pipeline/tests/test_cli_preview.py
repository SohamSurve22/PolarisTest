"""Tests for the development preview CLI command."""

import json
from pathlib import Path

import pytest

from document_pipeline.cli.main import main


def test_preview_from_text_prints_json_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
  text = "1. Scope\n\nThe Partner shall comply."

  exit_code = main(["preview", "--text", text])

  captured = capsys.readouterr()
  assert exit_code == 0
  payload = json.loads(captured.out)
  assert payload["cleaned_text"] == text
  assert payload["metadata"]["filename"].endswith(".txt")
  assert payload["sections"]
  assert payload["clauses"]


def test_preview_from_file_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
  file_path = tmp_path / "privacy_policy.txt"
  file_path.write_text("Privacy Policy\n\nWe collect data.\n", encoding="utf-8")

  exit_code = main(["preview", str(file_path)])

  captured = capsys.readouterr()
  assert exit_code == 0
  payload = json.loads(captured.out)
  assert payload["metadata"]["filename"] == "privacy_policy.txt"
  assert "Privacy Policy" in payload["raw_text"]
  assert payload["clauses"]


def test_preview_writes_output_file(tmp_path: Path) -> None:
  file_path = tmp_path / "policy.txt"
  output_path = tmp_path / "preview.json"
  file_path.write_text("ARTICLE I\n\nThe Partner shall comply.\n", encoding="utf-8")

  exit_code = main(["preview", str(file_path), "--output", str(output_path)])

  assert exit_code == 0
  payload = json.loads(output_path.read_text(encoding="utf-8"))
  assert payload["sections"][0]["section_id"] == "S001"
  assert payload["clauses"][0]["clause_id"] == "S001_C001"
  assert payload["clauses"][0]["clause_text"]
  assert payload["metadata"]["document_id"].startswith("DOC_")


def test_preview_preserves_unicode(capsys: pytest.CaptureFixture[str]) -> None:
  text = "Política de privacidad\n\nEl usuario acepta los términos."

  exit_code = main(["preview", "--text", text])

  captured = capsys.readouterr()
  assert exit_code == 0
  assert "Política de privacidad" in captured.out
  payload = json.loads(captured.out)
  assert payload["cleaned_text"] == text


def test_preview_includes_section_and_clause_mappings(
  capsys: pytest.CaptureFixture[str],
) -> None:
  text = "1. Scope\n\nFirst sentence. Second sentence."

  exit_code = main(["preview", "--text", text])

  captured = capsys.readouterr()
  assert exit_code == 0
  payload = json.loads(captured.out)
  section = payload["sections"][0]
  clause = payload["clauses"][0]

  assert section["span"]["start"] == 0
  assert section["span"]["end"] > section["span"]["start"]
  assert clause["section_id"] == section["section_id"]
  assert clause["clause_text"]
  assert clause["document_id"] == payload["metadata"]["document_id"]
  assert clause["document_type"] == payload["metadata"]["format"]
  assert clause["span"]["start"] >= 0


def test_preview_rejects_path_and_text_together(capsys: pytest.CaptureFixture[str]) -> None:
  exit_code = main(["preview", "policy.txt", "--text", "inline"])

  captured = capsys.readouterr()
  assert exit_code == 2
  assert "not both" in captured.err


def test_preview_requires_input(capsys: pytest.CaptureFixture[str]) -> None:
  exit_code = main(["preview"])

  captured = capsys.readouterr()
  assert exit_code == 2
  assert "provide a file path or --text" in captured.err


def test_preview_rejects_unsupported_extension(
  tmp_path: Path,
  capsys: pytest.CaptureFixture[str],
) -> None:
  file_path = tmp_path / "notes.xyz"
  file_path.write_text("unsupported", encoding="utf-8")

  exit_code = main(["preview", str(file_path)])

  captured = capsys.readouterr()
  assert exit_code == 1
  assert "Unsupported file type" in captured.err
