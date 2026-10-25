"""Jurisdiction registry for configurable law catalogs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class JurisdictionSpec:
  code: str
  aliases: tuple[str, ...] = ()
  law_dir: Path | None = None
  duty_rules_path: Path | None = None
  law_versions_path: Path | None = None

  @property
  def all_codes(self) -> tuple[str, ...]:
    return (self.code, *self.aliases)


class JurisdictionRegistry:
  def __init__(self, specs: tuple[JurisdictionSpec, ...]) -> None:
    self._by_code: dict[str, JurisdictionSpec] = {}
    for spec in specs:
      for code in spec.all_codes:
        normalized = _normalize(code)
        if normalized in self._by_code:
          raise ValueError(f"Duplicate jurisdiction code: {code}")
        self._by_code[normalized] = spec

  def resolve(self, code: str | None) -> JurisdictionSpec:
    normalized = _normalize(code or "IN")
    try:
      return self._by_code[normalized]
    except KeyError as exc:
      raise ValueError(f"Unsupported jurisdiction: {code}") from exc

  def supported_codes(self) -> frozenset[str]:
    return frozenset(self._by_code)


def default_registry(repo_root: Path | None = None) -> JurisdictionRegistry:
  root = repo_root or Path.cwd()
  dataset = root / "dataset"
  built_in = JurisdictionSpec(
    code="IN",
    aliases=("INDIA", "IN-DPDP"),
    law_dir=dataset,
  )
  configured = _configured_specs()
  return JurisdictionRegistry((built_in, *configured))


def _configured_specs() -> tuple[JurisdictionSpec, ...]:
  raw = os.environ.get("POLARIS_JURISDICTIONS_JSON", "").strip()
  if not raw:
    return ()
  try:
    payload = json.loads(raw)
  except json.JSONDecodeError as exc:
    raise ValueError("POLARIS_JURISDICTIONS_JSON must be valid JSON") from exc
  if not isinstance(payload, dict):
    raise ValueError("POLARIS_JURISDICTIONS_JSON must be an object")
  specs: list[JurisdictionSpec] = []
  for code, config in payload.items():
    if not isinstance(config, dict):
      raise ValueError(f"Jurisdiction config for {code} must be an object")
    law_dir = _path(config.get("law_dir"))
    if law_dir is None:
      raise ValueError(f"Jurisdiction config for {code} requires law_dir")
    aliases = config.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(item, str) for item in aliases):
      raise ValueError(f"Jurisdiction aliases for {code} must be a string array")
    specs.append(
      JurisdictionSpec(
        code=_normalize(str(code)),
        aliases=tuple(_normalize(item) for item in aliases),
        law_dir=law_dir,
        duty_rules_path=_path(config.get("duty_rules")),
        law_versions_path=_path(config.get("law_versions")),
      ),
    )
  return tuple(specs)


def law_paths_for(spec: JurisdictionSpec) -> list[Path]:
  if spec.law_dir is None:
    return []
  return sorted(path for path in spec.law_dir.glob("*.json") if path.is_file())


def _path(value: object) -> Path | None:
  if value is None or not str(value).strip():
    return None
  return Path(str(value)).expanduser()


def _normalize(code: str) -> str:
  return code.strip().upper()
