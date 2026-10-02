"""Scraper configuration (environment overridable, no secrets)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _env_float(name: str, default: float) -> float:
  return float(os.environ.get(name, default))


def _env_int(name: str, default: int) -> int:
  return int(os.environ.get(name, default))


@dataclass
class ScraperConfig:
  """Runtime settings. Defaults are deliberately conservative."""

  data_dir: Path = field(
    default_factory=lambda: Path(
      os.environ.get("POLICY_SCRAPER_DATA_DIR", PACKAGE_ROOT / "data" / "policies")
    )
  )
  timeout_s: float = field(default_factory=lambda: _env_float("POLICY_SCRAPER_TIMEOUT", 25.0))
  browser_timeout_s: float = field(
    default_factory=lambda: _env_float("POLICY_SCRAPER_BROWSER_TIMEOUT", 45.0)
  )
  max_redirects: int = 10
  http_retries: int = field(default_factory=lambda: _env_int("POLICY_SCRAPER_RETRIES", 1))
  max_concurrency: int = field(default_factory=lambda: _env_int("POLICY_SCRAPER_CONCURRENCY", 4))
  domain_delay_s: float = field(
    default_factory=lambda: _env_float("POLICY_SCRAPER_DOMAIN_DELAY", 3.0)
  )
  # Tiers tried in order. "stealth" additionally requires allow_stealth.
  tiers: tuple[str, ...] = ("http", "dynamic")
  allow_stealth: bool = False
  respect_robots: bool = True
  # RFC 9309: an unreachable robots.txt (5xx / network error) means "disallow".
  robots_unreachable: str = "deny"
  user_agent_token: str = "PolarisLexPolicyBot"
  max_pdf_bytes: int = 30 * 1024 * 1024
  min_chars: int = 800
  min_words: int = 120

  def __post_init__(self) -> None:
    self.data_dir = Path(self.data_dir).resolve()

  @property
  def raw_dir(self) -> Path:
    return self.data_dir / "raw"

  @property
  def processed_dir(self) -> Path:
    return self.data_dir / "processed"

  @property
  def metadata_dir(self) -> Path:
    return self.data_dir / "metadata"

  @property
  def failures_dir(self) -> Path:
    return self.data_dir / "failures"

  def ensure_dirs(self) -> None:
    for path in (self.raw_dir, self.processed_dir, self.metadata_dir, self.failures_dir):
      path.mkdir(parents=True, exist_ok=True)
