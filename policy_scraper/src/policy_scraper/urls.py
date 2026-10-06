"""CSV loading, URL validation and deterministic company identifiers."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

_MISSING_TOKENS = {"", "none", "null", "n/a", "na", "nan", "-"}
_REQUIRED_COLUMNS = ("company_name", "rank", "website", "policy_url")


@dataclass
class InputRow:
  """One validated CSV row. Original values are preserved alongside cleaned ones."""

  row_index: int
  company_id: str
  company_name: str
  rank: int | None
  website: str
  policy_url: str  # cleaned; empty when missing or invalid
  raw_policy_url: str
  issues: list[str] = field(default_factory=list)

  @property
  def fetchable(self) -> bool:
    return bool(self.policy_url)


def slugify(value: str) -> str:
  text = value.lower().replace("&", " and ")
  text = re.sub(r"[^a-z0-9]+", "-", text)
  return text.strip("-") or "company"


def clean_cell(value: str | None) -> str:
  """Collapse embedded newlines/tabs and surrounding whitespace in a CSV cell."""
  return re.sub(r"\s+", " ", (value or "").replace(" ", " ")).strip()


def make_company_id(rank: int | None, name: str, row_index: int) -> str:
  """Deterministic id: rank-slug (falls back to the row index when rank is missing)."""
  prefix = f"{rank:03d}" if rank is not None else f"r{row_index:04d}"
  return f"{prefix}-{slugify(name)}"


def validate_url(raw: str) -> tuple[str, list[str]]:
  """Return (cleaned_url, issues). cleaned_url is empty if unusable."""
  issues: list[str] = []
  text = clean_cell(raw)
  if text.lower() in _MISSING_TOKENS:
    return "", ["missing_policy_url"]
  if " " in text:
    issues.append("whitespace_in_url")
    text = text.replace(" ", "%20")
  parts = urlsplit(text)
  if parts.scheme not in ("http", "https"):
    return "", ["invalid_url_scheme"]
  host = parts.hostname or ""
  if not host or "." not in host:
    return "", ["invalid_url_host"]
  if parts.scheme == "http":
    issues.append("http_scheme")
  if parts.path.startswith("//"):
    issues.append("malformed_double_slash_path")
  return urlunsplit(parts), issues


def normalize_for_dedupe(url: str) -> str:
  parts = urlsplit(url)
  host = (parts.hostname or "").lower().removeprefix("www.")
  path = parts.path.rstrip("/")
  return f"{host}{path}?{parts.query}"


def load_rows(path: Path) -> list[InputRow]:
  """Read the CSV dynamically and validate every row. Nothing is silently dropped."""
  with path.open(newline="", encoding="utf-8-sig") as handle:
    reader = csv.DictReader(handle)
    header = [clean_cell(h).lower() for h in (reader.fieldnames or [])]
    missing = [col for col in _REQUIRED_COLUMNS if col not in header]
    if missing:
      msg = f"CSV is missing required columns: {missing}"
      raise ValueError(msg)
    reader.fieldnames = header
    raw_rows = list(reader)

  rows: list[InputRow] = []
  for index, raw in enumerate(raw_rows, start=1):
    issues: list[str] = []
    name = clean_cell(raw.get("company_name"))
    if not name:
      issues.append("missing_company_name")
      name = f"unknown-{index}"
    rank_text = clean_cell(raw.get("rank"))
    try:
      rank: int | None = int(rank_text)
    except ValueError:
      rank = None
      issues.append("invalid_rank")
    website = clean_cell(raw.get("website"))
    if not website:
      issues.append("missing_website")
    url, url_issues = validate_url(raw.get("policy_url") or "")
    issues.extend(url_issues)
    rows.append(
      InputRow(
        row_index=index,
        company_id=make_company_id(rank, name, index),
        company_name=name,
        rank=rank,
        website=website,
        policy_url=url,
        raw_policy_url=raw.get("policy_url") or "",
        issues=issues,
      )
    )
  _flag_duplicates(rows)
  return rows


def _flag_duplicates(rows: list[InputRow]) -> None:
  first_by_url: dict[str, InputRow] = {}
  first_by_name: dict[str, InputRow] = {}
  seen_ids: set[str] = set()
  for row in rows:
    if row.company_id in seen_ids:
      row.issues.append("duplicate_company_id")
      row.company_id = f"{row.company_id}-{row.row_index}"
    seen_ids.add(row.company_id)
    key = slugify(row.company_name)
    if key in first_by_name:
      row.issues.append(f"duplicate_company:{first_by_name[key].company_id}")
    first_by_name.setdefault(key, row)
    if row.policy_url:
      norm = normalize_for_dedupe(row.policy_url)
      if norm in first_by_url:
        row.issues.append(f"duplicate_url:{first_by_url[norm].company_id}")
      first_by_url.setdefault(norm, row)
