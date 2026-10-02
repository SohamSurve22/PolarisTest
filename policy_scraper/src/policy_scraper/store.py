"""Crash-safe per-company state. metadata/<company_id>.json is the source of truth."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from policy_scraper.config import ScraperConfig


def content_hash(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_name(path.name + ".tmp")
  tmp.write_bytes(data)
  try:
    os.replace(tmp, path)
  except OSError:
    tmp.unlink(missing_ok=True)  # never leave a stray .tmp behind (e.g. target locked on Windows)
    raise


def atomic_write_text(path: Path, text: str) -> None:
  atomic_write_bytes(path, text.encode("utf-8"))


class PolicyStore:
  def __init__(self, cfg: ScraperConfig) -> None:
    self.cfg = cfg
    cfg.ensure_dirs()

  def meta_path(self, company_id: str) -> Path:
    return self.cfg.metadata_dir / f"{company_id}.json"

  def save_record(self, record: dict[str, Any]) -> None:
    atomic_write_text(
      self.meta_path(record["company_id"]),
      json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
    )

  def load_record(self, company_id: str) -> dict[str, Any] | None:
    path = self.meta_path(company_id)
    if not path.is_file():
      return None
    try:
      return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
      return None  # corrupted (e.g. crash mid-write of an old copy): treat as not scraped

  def status(self, company_id: str) -> str | None:
    record = self.load_record(company_id)
    return record.get("scraping_status") if record else None

  def save_raw(self, company_id: str, body: bytes, ext: str) -> Path:
    path = self.cfg.raw_dir / f"{company_id}.{ext}"
    atomic_write_bytes(path, body)
    return path

  def save_processed(self, company_id: str, text: str) -> Path:
    path = self.cfg.processed_dir / f"{company_id}.txt"
    atomic_write_text(path, text)
    return path

  def load_processed(self, record: dict[str, Any]) -> str:
    rel = record.get("processed_path")
    if not rel:
      return ""
    path = self.cfg.data_dir / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""

  def all_records(self) -> list[dict[str, Any]]:
    records = []
    for path in sorted(self.cfg.metadata_dir.glob("*.json")):
      try:
        records.append(json.loads(path.read_text(encoding="utf-8")))
      except json.JSONDecodeError:
        continue
    records.sort(key=lambda r: (r.get("rank") is None, r.get("rank") or 0, r["company_id"]))
    return records
