from pathlib import Path

import pytest

from compliance.jurisdictions import JurisdictionRegistry, JurisdictionSpec, default_registry, law_paths_for


def test_builtin_aliases_resolve_to_canonical_india() -> None:
  spec = JurisdictionRegistry((JurisdictionSpec("IN", aliases=("INDIA",)),)).resolve("india")
  assert spec.code == "IN"


def test_environment_registry_adds_a_custom_catalog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  law_dir = tmp_path / "laws"
  law_dir.mkdir()
  (law_dir / "alpha.json").write_text("{}", encoding="utf-8")
  monkeypatch.setenv(
    "POLARIS_JURISDICTIONS_JSON",
    '{"EU": {"aliases": ["EUROPE"], "law_dir": "' + str(law_dir).replace("\\", "\\\\") + '"}}',
  )

  registry = default_registry(tmp_path)
  spec = registry.resolve("europe")

  assert spec.code == "EU"
  assert law_paths_for(spec) == [law_dir / "alpha.json"]


def test_unknown_jurisdiction_fails_closed() -> None:
  with pytest.raises(ValueError, match="Unsupported jurisdiction"):
    default_registry(Path.cwd()).resolve("US")
