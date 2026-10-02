"""robots.txt compliance and per-host rate limiting."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from protego import Protego

from policy_scraper.config import ScraperConfig

logger = logging.getLogger(__name__)

ROBOTS_RETRIES = 3


@dataclass
class RobotsDecision:
  allowed: bool
  status: str  # allowed | disallowed | no_robots | unreachable_allowed | unreachable_denied
  crawl_delay: float | None = None
  reason: str = ""  # why robots.txt was unreachable (dns_error, timeout, http_503 ...)


class Politeness:
  """Thread-safe robots cache and per-host minimum delay."""

  def __init__(self, cfg: ScraperConfig) -> None:
    self._cfg = cfg
    self._robots: dict[str, tuple[Protego | None, str]] = {}
    self._robots_lock = threading.Lock()
    self._host_locks: dict[str, threading.Lock] = {}
    self._last_hit: dict[str, float] = {}
    self._guard = threading.Lock()

  def _load_robots(self, origin: str) -> tuple[Protego | None, str]:
    from scrapling.fetchers import Fetcher

    from policy_scraper.fetch import classify_exception

    try:
      resp = Fetcher.get(
        f"{origin}/robots.txt", timeout=self._cfg.timeout_s, follow_redirects=True,
        retries=ROBOTS_RETRIES, retry_delay=2,  # transient DNS/network blips must not become a denial
      )
    except Exception as exc:
      logger.info("robots.txt unreachable for %s: %s", origin, exc)
      return None, "unreachable:" + classify_exception(exc)
    status = int(resp.status)
    if status == 200:
      text = bytes(resp.body or b"").decode("utf-8", errors="replace")
      if "<html" in text[:500].lower():  # HTML error page served as 200
        return None, "no_robots"
      return Protego.parse(text), "ok"
    if 400 <= status < 500:
      return None, "no_robots"
    return None, f"unreachable:http_{status}"

  def check(self, url: str) -> RobotsDecision:
    if not self._cfg.respect_robots:
      return RobotsDecision(True, "robots_ignored_by_config")
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    with self._robots_lock:
      if origin not in self._robots:
        self._robots[origin] = self._load_robots(origin)
      parser, state = self._robots[origin]
    if state == "no_robots":
      return RobotsDecision(True, "no_robots")
    if state.startswith("unreachable"):
      allow = self._cfg.robots_unreachable == "allow"
      return RobotsDecision(
        allow, "unreachable_allowed" if allow else "unreachable_denied", reason=state.partition(":")[2]
      )
    assert parser is not None
    token = self._cfg.user_agent_token
    allowed = parser.can_fetch(url, token) and parser.can_fetch(url, "*")
    delay = parser.crawl_delay(token) or parser.crawl_delay("*")
    return RobotsDecision(allowed, "allowed" if allowed else "disallowed", float(delay) if delay else None)

  def wait_turn(self, url: str, crawl_delay: float | None = None) -> None:
    """Block until the per-host delay has elapsed (serialises requests to one host)."""
    host = (urlsplit(url).hostname or "").lower()
    with self._guard:
      lock = self._host_locks.setdefault(host, threading.Lock())
    delay = max(self._cfg.domain_delay_s, crawl_delay or 0.0)
    with lock:
      wait = self._last_hit.get(host, 0.0) + delay - time.monotonic()
      if wait > 0:
        time.sleep(wait)
      self._last_hit[host] = time.monotonic()
