"""Fetching with Scrapling: HTTP -> dynamic (browser) -> stealth (opt-in) fallback.

Only public pages are requested. Cloudflare/CAPTCHA solving is never enabled and
blocked sites are recorded as failures instead of being retried indefinitely.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from policy_scraper.config import ScraperConfig

logger = logging.getLogger(__name__)

_BROWSER_LOCK = threading.Lock()  # one browser at a time (memory + thread-safety)


@dataclass
class FetchResult:
  tier: str
  ok: bool
  status: int | None = None
  final_url: str = ""
  content_type: str = ""
  body: bytes = b""
  encoding: str | None = None
  redirect_chain: list[dict] = field(default_factory=list)
  error_kind: str | None = None
  error: str | None = None
  elapsed_s: float = 0.0

  @property
  def is_pdf(self) -> bool:
    return "pdf" in self.content_type.lower() or self.body[:5] == b"%PDF-"


def _chain_from_history(response: object, original: str) -> list[dict]:
  chain: list[dict] = []
  for hop in getattr(response, "history", None) or []:
    headers = getattr(hop, "headers", {}) or {}
    chain.append(
      {
        "url": str(getattr(hop, "url", "")),
        "status": getattr(hop, "status_code", None) or getattr(hop, "status", None),
        "location": headers.get("location") or headers.get("Location"),
      }
    )
  if not chain and str(getattr(response, "url", original)) != original:
    chain.append({"url": original, "status": None, "location": str(getattr(response, "url", ""))})
  chain.append({"url": str(getattr(response, "url", original)), "status": getattr(response, "status", None), "location": None})
  return chain


def classify_exception(exc: Exception) -> str:
  text = f"{type(exc).__name__} {exc}".lower()
  if "redirect" in text and ("too many" in text or "max" in text or "loop" in text):
    return "redirect_loop"
  if "timed out" in text or "timeout" in text:
    return "timeout"
  if "ssl" in text or "certificate" in text:
    return "ssl_error"
  if "resolve" in text or "name or service" in text or "getaddrinfo" in text or "dns" in text:
    return "dns_error"
  if "connect" in text or "reset" in text or "refused" in text:
    return "connection_error"
  return "fetch_exception"


def fetch_http(url: str, cfg: ScraperConfig) -> FetchResult:
  """Tier 1: plain Scrapling HTTP fetch (curl_cffi under the hood)."""
  from scrapling.fetchers import Fetcher

  started = time.monotonic()
  try:
    resp = Fetcher.get(
      url,
      timeout=cfg.timeout_s,
      follow_redirects=True,
      max_redirects=cfg.max_redirects,
      retries=cfg.http_retries,
      retry_delay=2,
    )
  except Exception as exc:  # network layer: record, never swallow silently
    logger.warning("http fetch failed for %s: %s", url, exc)
    return FetchResult(
      tier="http", ok=False, final_url=url, error_kind=classify_exception(exc),
      error=f"{type(exc).__name__}: {exc}", elapsed_s=time.monotonic() - started,
    )
  body = bytes(resp.body or b"")
  ctype = str(resp.headers.get("content-type") or resp.headers.get("Content-Type") or "")
  status = int(resp.status)
  result = FetchResult(
    tier="http", ok=200 <= status < 300, status=status, final_url=str(resp.url),
    content_type=ctype, body=body, encoding=getattr(resp, "encoding", None),
    redirect_chain=_chain_from_history(resp, url), elapsed_s=time.monotonic() - started,
  )
  if not result.ok:
    result.error_kind = {403: "blocked_403", 429: "rate_limited_429", 404: "not_found_404"}.get(
      status, f"http_{status}"
    )
    result.error = f"HTTP {status}"
  elif len(body) > cfg.max_pdf_bytes:
    result.ok = False
    result.error_kind = "too_large"
    result.error = f"body {len(body)} bytes exceeds limit"
  return result


def _browser_result(tier: str, url: str, resp: object, started: float) -> FetchResult:
  status = int(getattr(resp, "status", 0) or 0)
  headers = getattr(resp, "headers", {}) or {}
  body = bytes(getattr(resp, "body", b"") or b"")
  result = FetchResult(
    tier=tier, ok=200 <= status < 300, status=status, final_url=str(getattr(resp, "url", url)),
    content_type=str(headers.get("content-type") or headers.get("Content-Type") or "text/html"),
    body=body, encoding=getattr(resp, "encoding", None),
    redirect_chain=_chain_from_history(resp, url), elapsed_s=time.monotonic() - started,
  )
  if not result.ok:
    # Same labels as the HTTP tier so the escalation rules treat both tiers alike.
    result.error_kind = {403: "blocked_403", 429: "rate_limited_429"}.get(status, f"http_{status}")
    result.error = f"HTTP {status}"
  return result


def fetch_dynamic(url: str, cfg: ScraperConfig) -> FetchResult:
  """Tier 2: Playwright-driven rendering for JavaScript pages."""
  started = time.monotonic()
  try:
    from scrapling.fetchers import DynamicFetcher

    with _BROWSER_LOCK:
      resp = DynamicFetcher.fetch(
        url, headless=True, network_idle=True, disable_resources=True,
        timeout=int(cfg.browser_timeout_s * 1000), retries=1,
      )
  except Exception as exc:
    logger.warning("dynamic fetch failed for %s: %s", url, exc)
    kind = "browser_not_installed" if "executable" in str(exc).lower() else classify_exception(exc)
    return FetchResult(
      tier="dynamic", ok=False, final_url=url, error_kind=kind,
      error=f"{type(exc).__name__}: {str(exc)[:300]}", elapsed_s=time.monotonic() - started,
    )
  return _browser_result("dynamic", url, resp, started)


def fetch_stealth(url: str, cfg: ScraperConfig) -> FetchResult:
  """Tier 3 (opt-in): Scrapling StealthyFetcher. Never solves challenges."""
  started = time.monotonic()
  try:
    from scrapling.fetchers import StealthyFetcher

    with _BROWSER_LOCK:
      resp = StealthyFetcher.fetch(
        url, headless=True, network_idle=True, solve_cloudflare=False,
        timeout=int(cfg.browser_timeout_s * 1000), retries=1,
      )
  except Exception as exc:
    logger.warning("stealth fetch failed for %s: %s", url, exc)
    kind = "browser_not_installed" if "executable" in str(exc).lower() else classify_exception(exc)
    return FetchResult(
      tier="stealth", ok=False, final_url=url, error_kind=kind,
      error=f"{type(exc).__name__}: {str(exc)[:300]}", elapsed_s=time.monotonic() - started,
    )
  return _browser_result("stealth", url, resp, started)


TIER_FUNCS = {"http": fetch_http, "dynamic": fetch_dynamic, "stealth": fetch_stealth}


def host_of(url: str) -> str:
  return (urlsplit(url).hostname or "").lower()
