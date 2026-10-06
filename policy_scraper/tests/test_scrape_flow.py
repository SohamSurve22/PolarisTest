"""Scrape orchestration with mocked fetchers: fallback, redirects, resume, status tracking."""

from pathlib import Path

import pytest

from policy_scraper import fetch as fetch_mod
from policy_scraper import scrape
from policy_scraper.config import ScraperConfig
from policy_scraper.fetch import FetchResult
from policy_scraper.politeness import RobotsDecision
from policy_scraper.store import PolicyStore
from policy_scraper.urls import InputRow

BODY = ("<html><head><title>Privacy</title></head><body><main><h1>Privacy Policy</h1>"
        + "".join(
          f"<p>Section {i}: We collect personal information and cookies and share data with third parties and "
          f"service providers. You have rights to opt out of item {i}. Contact us about privacy. We retain data "
          f"and apply security measures to record {i}.</p>" for i in range(14))
        + "</main></body></html>").encode()
EMPTY = b"<html><body><noscript>enable javascript</noscript><div id='root'></div></body></html>"


class FakePoliteness:
  def __init__(self, decision: RobotsDecision | None = None) -> None:
    self.decision = decision or RobotsDecision(True, "no_robots")

  def check(self, url: str) -> RobotsDecision:
    return self.decision

  def wait_turn(self, url: str, crawl_delay: float | None = None) -> None:
    return None


def _row(n: int = 1, url: str = "https://acme.test/privacy") -> InputRow:
  return InputRow(row_index=n, company_id=f"{n:03d}-acme", company_name="Acme", rank=n,
                  website="http://acme.test", policy_url=url, raw_policy_url=url)


def _ok(body: bytes, tier: str = "http", final: str = "https://acme.test/privacy",
        ctype: str = "text/html", chain=None) -> FetchResult:
  return FetchResult(tier=tier, ok=True, status=200, final_url=final, content_type=ctype, body=body,
                     redirect_chain=chain or [{"url": "https://acme.test/privacy", "status": 200, "location": None}])


@pytest.fixture
def cfg(tmp_path: Path) -> ScraperConfig:
  return ScraperConfig(data_dir=tmp_path / "out")


def _patch(monkeypatch: pytest.MonkeyPatch, **tiers) -> list[str]:
  calls: list[str] = []
  for name in ("http", "dynamic", "stealth"):
    fn = tiers.get(name)
    if fn is None:
      monkeypatch.setitem(scrape.TIER_FUNCS, name, lambda u, c, n=name: pytest.fail(f"unexpected {n} tier"))
    else:
      monkeypatch.setitem(scrape.TIER_FUNCS, name, (lambda u, c, n=name, f=fn: (calls.append(n), f(u, c))[1]))
  return calls


def test_http_success_writes_processed_and_hash(monkeypatch, cfg) -> None:
  _patch(monkeypatch, http=lambda u, c: _ok(BODY))
  store = PolicyStore(cfg)
  rec = scrape.scrape_one(_row(), cfg, store, FakePoliteness())
  assert rec["scraping_status"] == "success" and rec["scrape_tier"] == "http"
  assert rec["document_type"] == "html" and rec["content_hash"] and rec["content_length"] > 800
  assert (cfg.data_dir / rec["processed_path"]).is_file()
  assert (cfg.data_dir / rec["raw_path"]).read_bytes() == BODY
  assert store.status("001-acme") == "success"


def test_200_with_empty_content_escalates_to_dynamic(monkeypatch, cfg) -> None:
  calls = _patch(monkeypatch, http=lambda u, c: _ok(EMPTY), dynamic=lambda u, c: _ok(BODY, tier="dynamic"))
  rec = scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())
  assert calls == ["http", "dynamic"]
  assert rec["scraping_status"] == "success" and rec["scrape_tier"] == "dynamic"
  assert rec["tiers_attempted"][0]["quality_issues"]  # HTTP 200 was not accepted as success


def test_200_empty_everywhere_is_failure_not_success(monkeypatch, cfg) -> None:
  _patch(monkeypatch, http=lambda u, c: _ok(EMPTY), dynamic=lambda u, c: _ok(EMPTY, tier="dynamic"))
  rec = scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())
  assert rec["scraping_status"] == "failed" and rec["error_kind"].startswith("quality_")
  assert rec["processed_path"] is None


def test_403_and_404_escalate_once_to_browser_only(monkeypatch, cfg) -> None:
  def forbidden(u, c):
    return FetchResult(tier="http", ok=False, status=403, final_url=u, error_kind="blocked_403", error="HTTP 403")

  def missing(u, c):
    return FetchResult(tier="http", ok=False, status=404, final_url=u, error_kind="not_found_404", error="HTTP 404")

  calls = _patch(monkeypatch, http=forbidden, dynamic=lambda u, c: _ok(BODY, tier="dynamic"))
  assert scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())["scraping_status"] == "success"
  assert calls == ["http", "dynamic"]
  # genuine 404: re-checked once in the browser, never sent to stealth
  cfg.allow_stealth = True
  dyn_404 = lambda u, c: FetchResult(tier="dynamic", ok=False, status=404, final_url=u, error_kind="http_404")  # noqa: E731
  calls = _patch(monkeypatch, http=missing, dynamic=dyn_404)
  rec = scrape.scrape_one(_row(2), cfg, PolicyStore(cfg), FakePoliteness())
  assert rec["error_kind"] == "http_404" and calls == ["http", "dynamic"]
  # WAF-style 404: browser gets the real page
  calls = _patch(monkeypatch, http=missing, dynamic=lambda u, c: _ok(BODY, tier="dynamic"))
  assert scrape.scrape_one(_row(3), cfg, PolicyStore(cfg), FakePoliteness())["scrape_tier"] == "dynamic"


def test_stealth_only_when_enabled(monkeypatch, cfg) -> None:
  blocked = lambda u, c: FetchResult(tier="x", ok=False, status=403, final_url=u, error_kind="blocked_403")  # noqa: E731
  calls = _patch(monkeypatch, http=blocked, dynamic=blocked)
  scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())
  assert "stealth" not in calls
  cfg.allow_stealth = True
  calls = _patch(monkeypatch, http=blocked, dynamic=blocked, stealth=lambda u, c: _ok(BODY, tier="stealth"))
  rec = scrape.scrape_one(_row(3), cfg, PolicyStore(cfg), FakePoliteness())
  assert calls == ["http", "dynamic", "stealth"] and rec["scrape_tier"] == "stealth"


def test_redirect_recorded_and_homepage_redirect_rejected(monkeypatch, cfg) -> None:
  chain = [{"url": "https://acme.test/privacy", "status": 301, "location": "/"},
           {"url": "https://acme.test/", "status": 200, "location": None}]
  _patch(monkeypatch, http=lambda u, c: _ok(BODY, final="https://acme.test/", chain=chain))
  rec = scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())
  assert rec["scraping_status"] == "failed" and rec["error_kind"] == "redirect_to_homepage"
  assert rec["final_policy_url"] == "https://acme.test/" and len(rec["redirect_chain"]) == 2


def test_domain_change_is_flagged_but_kept(monkeypatch, cfg) -> None:
  chain = [{"url": "https://acme.test/privacy", "status": 302, "location": "https://other.org/p"},
           {"url": "https://other.org/p", "status": 200, "location": None}]
  _patch(monkeypatch, http=lambda u, c: _ok(BODY, final="https://other.org/p", chain=chain))
  rec = scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())
  assert rec["scraping_status"] == "success" and "domain_change" in rec["review_flags"]


def test_redirect_loop_detected(monkeypatch, cfg) -> None:
  chain = [{"url": "https://a.test/x", "status": 302, "location": None},
           {"url": "https://a.test/y", "status": 302, "location": None},
           {"url": "https://a.test/x", "status": 200, "location": None}]
  _patch(monkeypatch, http=lambda u, c: _ok(BODY, chain=chain))
  assert scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())["error_kind"] == "redirect_loop"


def test_robots_disallow_blocks_fetch(monkeypatch, cfg) -> None:
  _patch(monkeypatch)  # any fetch fails the test
  rec = scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness(RobotsDecision(False, "disallowed")))
  assert rec["error_kind"] == "robots_disallowed" and rec["failure_stage"] == "robots"


def test_missing_url_is_skipped_and_recorded(monkeypatch, cfg) -> None:
  _patch(monkeypatch)
  row = InputRow(1, "001-x", "X", 1, "http://x.com", "", "None", issues=["missing_policy_url"])
  rec = scrape.scrape_one(row, cfg, PolicyStore(cfg), FakePoliteness())
  assert rec["scraping_status"] == "skipped" and rec["error_kind"] == "missing_policy_url"


def test_pdf_goes_to_pdf_parser_not_html(monkeypatch, cfg) -> None:
  seen = {}

  def fake_pdf(body: bytes):
    seen["called"] = True
    return ("We collect personal information and cookies. " * 80 + " privacy third parties share", 3, "T", [])

  monkeypatch.setattr(scrape.extract, "extract_pdf", fake_pdf)
  monkeypatch.setattr(scrape.extract, "extract_html", lambda *a, **k: pytest.fail("PDF sent to HTML parser"))
  _patch(monkeypatch, http=lambda u, c: _ok(b"%PDF-1.7 fake", ctype="application/pdf", final="https://acme.test/p.pdf"))
  rec = scrape.scrape_one(_row(url="https://acme.test/p.pdf"), cfg, PolicyStore(cfg), FakePoliteness())
  assert seen["called"] and rec["document_type"] == "pdf" and rec["raw_path"].endswith(".pdf")


def test_exception_in_pipeline_is_recorded_not_raised(monkeypatch, cfg) -> None:
  def boom(u, c):
    raise RuntimeError("kaboom")

  _patch(monkeypatch, http=boom)
  rec = scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())
  assert rec["scraping_status"] == "failed" and rec["error_kind"] == "internal_error" and "kaboom" in rec["error"]


def test_resume_retry_failed_and_force_selection(monkeypatch, cfg) -> None:
  store = PolicyStore(cfg)
  rows = [_row(1), _row(2), _row(3)]
  rows[1].company_id, rows[2].company_id = "002-b", "003-c"
  store.save_record({"company_id": "001-acme", "scraping_status": "success", "rank": 1})
  store.save_record({"company_id": "002-b", "scraping_status": "failed", "rank": 2})
  assert [r.company_id for r in scrape.pending_rows(rows, store)] == ["003-c"]
  assert [r.company_id for r in scrape.pending_rows(rows, store, retry_failed=True)] == ["002-b"]
  assert len(scrape.pending_rows(rows, store, force=True)) == 3
  assert [r.company_id for r in scrape.pending_rows(rows, store, force=True, limit=2)] == ["001-acme", "002-b"]
  assert [r.company_id for r in scrape.pending_rows(rows, store, force=True, start_index=2)] == ["003-c"]
  assert [r.company_id for r in scrape.pending_rows(rows, store, force=True, company="003-c")] == ["003-c"]


def test_corrupt_metadata_treated_as_unscraped(cfg) -> None:
  store = PolicyStore(cfg)
  store.meta_path("009-z").write_text("{not json", encoding="utf-8")
  assert store.load_record("009-z") is None and store.status("009-z") is None


def test_duplicate_content_marked_and_exports_rebuilt(monkeypatch, cfg) -> None:
  _patch(monkeypatch, http=lambda u, c: _ok(BODY))
  store = PolicyStore(cfg)
  scrape.scrape_one(_row(1), cfg, store, FakePoliteness())
  second = _row(2)
  second.company_id = "002-acme2"
  scrape.scrape_one(second, cfg, store, FakePoliteness())
  paths = scrape.export_all(cfg, store)
  import json

  lines = [json.loads(x) for x in paths["jsonl"].read_text(encoding="utf-8").splitlines()]
  assert len(lines) == 2 and lines[0]["duplicate_of"] is None and lines[1]["duplicate_of"] == "001-acme"
  assert lines[0]["content"] and "duplicate_content" in lines[1]["quality_flags"]
  assert paths["csv"].is_file() and paths["failures"].read_text(encoding="utf-8") == ""


def test_fetch_chain_from_history_uses_status_code() -> None:
  class Hop:
    url = "https://a.test/old"
    status_code = 301
    headers = {"location": "/new"}

  class Resp:
    url = "https://a.test/new"
    status = 200
    history = [Hop()]

  chain = fetch_mod._chain_from_history(Resp(), "https://a.test/old")
  assert [(h["url"], h["status"]) for h in chain] == [("https://a.test/old", 301), ("https://a.test/new", 200)]
  assert chain[0]["location"] == "/new"


def test_browser_403_label_matches_http_tier_so_stealth_runs() -> None:
  class Resp:
    url = "https://a.test/p"
    status = 403
    headers: dict = {}
    body = b""
    history: list = []

  res = fetch_mod._browser_result("dynamic", "https://a.test/p", Resp(), 0.0)
  assert res.error_kind == "blocked_403" and "blocked_403" in scrape._STEALTH_ERRORS


def test_403_through_http_and_dynamic_reaches_stealth(monkeypatch, cfg) -> None:
  cfg.allow_stealth = True
  blocked = lambda u, c: FetchResult(tier="x", ok=False, status=403, final_url=u, error_kind="blocked_403")  # noqa: E731
  calls = _patch(monkeypatch, http=blocked, dynamic=blocked, stealth=lambda u, c: _ok(BODY, tier="stealth"))
  rec = scrape.scrape_one(_row(), cfg, PolicyStore(cfg), FakePoliteness())
  assert calls == ["http", "dynamic", "stealth"] and rec["scraping_status"] == "success"


def test_retry_kind_filter_selects_only_transient(cfg) -> None:
  store = PolicyStore(cfg)
  rows = [_row(1), _row(2), _row(3)]
  rows[1].company_id, rows[2].company_id = "002-b", "003-c"
  store.save_record({"company_id": "001-acme", "scraping_status": "failed", "rank": 1, "error_kind": "robots_unreachable_dns_error"})
  store.save_record({"company_id": "002-b", "scraping_status": "failed", "rank": 2, "error_kind": "http_404"})
  store.save_record({"company_id": "003-c", "scraping_status": "failed", "rank": 3, "error_kind": "http_503"})
  got = scrape.pending_rows(rows, store, retry_failed=True, retry_kinds=scrape.TRANSIENT_KINDS)
  assert [r.company_id for r in got] == ["001-acme", "003-c"]
  assert len(scrape.pending_rows(rows, store, retry_failed=True)) == 3


def test_robots_fetch_retries_transient_errors(monkeypatch, cfg) -> None:
  from policy_scraper import politeness

  seen = {}

  class Resp:
    status = 200
    body = b"User-agent: *\nDisallow: /private\n"

  def fake_get(url, **kw):
    seen.update(kw)
    return Resp()

  import scrapling.fetchers as sf

  monkeypatch.setattr(sf.Fetcher, "get", staticmethod(fake_get))
  pol = politeness.Politeness(cfg)
  assert pol.check("https://a.test/privacy").allowed and not pol.check("https://a.test/private/x").allowed
  assert seen["retries"] >= 2


def test_locked_export_falls_back_to_pending_file(monkeypatch, cfg) -> None:
  import os

  _patch(monkeypatch, http=lambda u, c: _ok(BODY))
  store = PolicyStore(cfg)
  scrape.scrape_one(_row(1), cfg, store, FakePoliteness())
  real_replace = os.replace

  def locked(src, dst):
    if str(dst).endswith("fortune500_policies_summary.csv"):
      raise PermissionError(13, "Access is denied")
    return real_replace(src, dst)

  monkeypatch.setattr("policy_scraper.store.os.replace", locked)
  paths = scrape.export_all(cfg, store)  # must not raise
  assert paths["csv"].name == "fortune500_policies_summary.pending.csv" and paths["csv"].is_file()
  assert paths["jsonl"].name == "fortune500_policies.jsonl"
  assert not list(cfg.data_dir.glob("*.tmp"))


def test_jsonl_line_escapes_unicode_line_separators() -> None:
  import json

  content = "a\u2028b\u2029c\x85d"
  line = scrape.jsonl_line({"content": content})
  assert line.endswith("\n") and len(line.splitlines()) == 1
  assert json.loads(line)["content"] == content


def test_exported_jsonl_survives_splitlines_with_separator_in_content(monkeypatch, cfg) -> None:
  import json

  body = BODY.replace(b"Privacy Policy", "Privacy\u2028Policy".encode())
  _patch(monkeypatch, http=lambda u, c: _ok(body))
  store = PolicyStore(cfg)
  scrape.scrape_one(_row(1), cfg, store, FakePoliteness())
  record = store.all_records()[0]
  store.save_processed(record["company_id"], store.load_processed(record) + "\nend\u2028of\x85text")
  lines = scrape.export_all(cfg, store)["jsonl"].read_text(encoding="utf-8").splitlines()
  assert len(lines) == 1 and "end\u2028of\x85text" in json.loads(lines[0])["content"]
