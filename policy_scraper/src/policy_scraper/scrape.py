"""Scrape orchestration: per-company fallback strategy, batching, resume, exports."""

from __future__ import annotations

import csv
import io
import json
import logging
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import scrapling

from policy_scraper import extract, quality
from policy_scraper.config import ScraperConfig
from policy_scraper.fetch import TIER_FUNCS, FetchResult
from policy_scraper.politeness import Politeness
from policy_scraper.store import PolicyStore, atomic_write_text, content_hash
from policy_scraper.urls import InputRow

logger = logging.getLogger(__name__)

# Fetch failures worth escalating to a browser tier. Everything else (DNS, SSL, timeouts,
# 429 ...) is recorded and not retried further. A plain-HTTP 404 is re-checked once in a real
# browser only: WAFs (e.g. Bank of America, PBF Energy) answer HTTP clients with 404 while
# serving browsers 200. It never escalates to the stealth tier.
_ESCALATE_ERRORS = {"blocked_403", "not_found_404"}
_STEALTH_ERRORS = {"blocked_403"}


def _now() -> str:
  return datetime.now(UTC).isoformat(timespec="seconds")


def _has_cycle(chain: list[dict]) -> bool:
  urls = [hop["url"] for hop in chain]
  return len(urls) != len(set(urls))


def _base_record(row: InputRow) -> dict[str, Any]:
  return {
    "company_id": row.company_id,
    "company_name": row.company_name,
    "rank": row.rank,
    "website": row.website,
    "original_policy_url": row.policy_url or row.raw_policy_url.strip(),
    "final_policy_url": "",
    "redirect_chain": [],
    "document_type": None,
    "scraping_status": "failed",
    "failure_stage": None,
    "http_status": None,
    "content_type": "",
    "title": "",
    "content_length": 0,
    "word_count": 0,
    "content_hash": "",
    "scraped_at": _now(),
    "scraper": "scrapling",
    "scraper_version": scrapling.__version__,
    "scrape_tier": None,
    "tiers_attempted": [],
    "quality_flags": [],
    "review_flags": [],
    "robots_status": None,
    "input_issues": list(row.issues),
    "raw_path": None,
    "processed_path": None,
    "elapsed_s": 0.0,
    "error_kind": None,
    "error": None,
  }


def _process_fetch(
  res: FetchResult, cfg: ScraperConfig
) -> tuple[str, str, str, list[str], quality.Verdict | None, str | None, str | None]:
  """Return (doc_type, text, title, extra_flags, verdict, error_kind, error)."""
  if res.is_pdf:
    try:
      text, _pages, title, notes = extract.extract_pdf(res.body)
    except Exception as exc:
      return "pdf", "", "", [], None, "pdf_parse_error", f"{type(exc).__name__}: {exc}"
    verdict = quality.assess(text, min_chars=cfg.min_chars, min_words=cfg.min_words)
    return "pdf", text, title or "", notes, verdict, None, None
  ctype = res.content_type.lower()
  if "html" in ctype or "xml" in ctype or not ctype or res.body.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
    html = extract.decode_html(res.body, res.encoding)
    content = extract.extract_html(html, url=res.final_url)
    verdict = quality.assess(
      content.text, min_chars=cfg.min_chars, min_words=cfg.min_words,
      has_noscript="has_noscript" in content.flags, title=content.title,
    )
    return "html", content.text, content.title, content.flags, verdict, None, None
  if "text/plain" in ctype:
    text = extract.normalize_text(extract.decode_html(res.body, res.encoding))
    verdict = quality.assess(text, min_chars=cfg.min_chars, min_words=cfg.min_words)
    return "text", text, "", [], verdict, None, None
  return "unknown", "", "", [], None, "unsupported_content_type", f"content-type {res.content_type!r}"


def scrape_one(row: InputRow, cfg: ScraperConfig, store: PolicyStore, politeness: Politeness) -> dict[str, Any]:
  """Scrape one company with the controlled fallback. Always returns (and saves) a record."""
  started = time.monotonic()
  rec = _base_record(row)
  try:
    _scrape_into(rec, row, cfg, store, politeness)
  except Exception as exc:  # last-resort guard: record the bug, keep the batch going
    logger.exception("unexpected error scraping %s", row.company_id)
    rec.update(scraping_status="failed", failure_stage="internal", error_kind="internal_error",
               error=f"{type(exc).__name__}: {exc}")
  rec["elapsed_s"] = round(time.monotonic() - started, 2)
  store.save_record(rec)
  logger.info("%s -> %s%s", row.company_id, rec["scraping_status"],
              f" ({rec['error_kind']})" if rec["error_kind"] else f" [{rec['scrape_tier']}]")
  return rec


def _scrape_into(rec: dict[str, Any], row: InputRow, cfg: ScraperConfig, store: PolicyStore, pol: Politeness) -> None:
  if not row.fetchable:
    rec.update(scraping_status="skipped", failure_stage="input",
               error_kind=next((i for i in row.issues if "url" in i), "invalid_input"),
               error="; ".join(row.issues) or "no usable policy URL")
    return

  url = row.policy_url
  decision = pol.check(url)
  rec["robots_status"] = decision.status
  if not decision.allowed:
    kind = "robots_disallowed" if decision.status == "disallowed" else f"robots_unreachable_{decision.reason or 'unknown'}"
    rec.update(failure_stage="robots", error_kind=kind, error=f"robots.txt: {decision.status} {decision.reason}".strip())
    return

  tiers = [t for t in cfg.tiers if t != "stealth"]
  if cfg.allow_stealth:
    tiers.append("stealth")

  for index, tier in enumerate(tiers):
    pol.wait_turn(url, decision.crawl_delay)
    res = TIER_FUNCS[tier](url, cfg)
    attempt: dict[str, Any] = {
      "tier": tier, "ok": res.ok, "status": res.status, "final_url": res.final_url,
      "elapsed_s": round(res.elapsed_s, 2), "error_kind": res.error_kind, "quality_issues": [],
    }
    rec["tiers_attempted"].append(attempt)
    rec["http_status"] = res.status
    rec["final_policy_url"] = res.final_url
    rec["redirect_chain"] = res.redirect_chain
    rec["content_type"] = res.content_type
    more = index + 1 < len(tiers)

    if not res.ok:
      rec.update(failure_stage="fetch", error_kind=res.error_kind, error=res.error)
      if res.error_kind in _ESCALATE_ERRORS and more:
        next_tier = tiers[index + 1]
        if next_tier != "stealth" or res.error_kind in _STEALTH_ERRORS:
          continue
      if res.error_kind == "browser_not_installed" and more:
        continue
      return

    if _has_cycle(res.redirect_chain):
      rec.update(failure_stage="fetch", error_kind="redirect_loop", error="redirect chain revisits a URL")
      return

    doc_type, text, title, flags, verdict, perr, perr_msg = _process_fetch(res, cfg)
    ext = {"pdf": "pdf", "html": "html", "text": "txt"}.get(doc_type, "bin")
    rec["raw_path"] = str(store.save_raw(row.company_id, res.body, ext).relative_to(cfg.data_dir)).replace("\\", "/")
    rec["document_type"] = doc_type
    rec["title"] = title
    if perr:
      rec.update(failure_stage="extract", error_kind=perr, error=perr_msg)
      return
    assert verdict is not None
    attempt["quality_issues"] = verdict.issues
    rec["quality_flags"] = sorted(set(flags + verdict.issues))
    rec["content_length"] = len(text)
    rec["word_count"] = verdict.words
    review = quality.review_redirect(url, res.final_url)
    rec["review_flags"] = review

    if not verdict.ok:
      rec.update(failure_stage="quality", error_kind="quality_" + verdict.issues[0],
                 error="content failed quality checks: " + ", ".join(verdict.issues))
      if verdict.needs_rendering and doc_type == "html" and more:
        continue
      return
    if "redirect_to_login" in review or "redirect_to_homepage" in review:
      rec.update(failure_stage="redirect_review", error_kind=review[0] if review[0].startswith("redirect_to") else review[-1],
                 error=f"redirect rejected: {review}")
      return

    rec["processed_path"] = str(store.save_processed(row.company_id, text).relative_to(cfg.data_dir)).replace("\\", "/")
    rec["content_hash"] = content_hash(text)
    rec.update(scraping_status="success", failure_stage=None, error_kind=None, error=None, scrape_tier=tier)
    return


def pending_rows(
  rows: list[InputRow],
  store: PolicyStore,
  *,
  retry_failed: bool = False,
  force: bool = False,
  company: str | None = None,
  start_index: int = 0,
  limit: int | None = None,
  retry_kinds: tuple[str, ...] = (),
) -> list[InputRow]:
  """Select rows to process: default = never attempted; --retry-failed = failed only.

  ``retry_kinds`` narrows --retry-failed to records whose error_kind starts with one of the prefixes
  (e.g. transient network failures) so permanent failures are not hammered again.
  """
  selected = rows[start_index:]
  if company:
    needle = company.lower()
    selected = [r for r in selected if needle in r.company_name.lower() or needle == r.company_id.lower()]
  out: list[InputRow] = []
  for row in selected:
    status = store.status(row.company_id)
    if force:
      out.append(row)
    elif retry_failed:
      if status == "failed" and _kind_matches(store, row.company_id, retry_kinds):
        out.append(row)
    elif status is None:
      out.append(row)
  return out[:limit] if limit else out


def _kind_matches(store: PolicyStore, company_id: str, kinds: tuple[str, ...]) -> bool:
  if not kinds:
    return True
  record = store.load_record(company_id) or {}
  return str(record.get("error_kind") or "").startswith(kinds)


TRANSIENT_KINDS = ("robots_unreachable", "timeout", "connection_error", "dns_error", "fetch_exception",
                   "http_5", "rate_limited", "ssl_error")


def run_batch(rows: list[InputRow], cfg: ScraperConfig, store: PolicyStore) -> list[dict[str, Any]]:
  politeness = Politeness(cfg)
  results: list[dict[str, Any]] = []
  pool = ThreadPoolExecutor(max_workers=max(1, cfg.max_concurrency))
  futures = {pool.submit(scrape_one, row, cfg, store, politeness): row for row in rows}
  try:
    for done, future in enumerate(as_completed(futures), start=1):
      results.append(future.result())
      if done % 10 == 0:
        logger.info("progress %d/%d", done, len(rows))
  except KeyboardInterrupt:
    logger.warning("interrupted: cancelling pending work; completed records are already saved")
    pool.shutdown(wait=False, cancel_futures=True)
    raise
  finally:
    pool.shutdown(wait=True, cancel_futures=True)
    export_all(cfg, store)
  return results


# ---------------------------------------------------------------- exports
_SUMMARY_COLUMNS = [
  "company_id", "company_name", "rank", "scraping_status", "failure_stage", "error_kind",
  "document_type", "scrape_tier", "http_status", "original_policy_url", "final_policy_url",
  "redirect_hops", "review_flags", "quality_flags", "content_length", "word_count",
  "content_hash", "duplicate_of", "title", "robots_status", "elapsed_s", "error",
]


def _mark_duplicates(records: list[dict[str, Any]]) -> None:
  first: dict[str, str] = {}
  for rec in records:
    rec["duplicate_of"] = None
    h = rec.get("content_hash")
    if rec.get("scraping_status") != "success" or not h:
      continue
    if h in first:
      rec["duplicate_of"] = first[h]
      if "duplicate_content" not in rec["quality_flags"]:
        rec["quality_flags"] = sorted({*rec["quality_flags"], "duplicate_content"})
    else:
      first[h] = rec["company_id"]


def jsonl_line(record: dict[str, Any]) -> str:
  """One JSON record per line. U+2028/U+2029/U+0085 are escaped: str.splitlines() and some readers
  treat them as line breaks, which would split a record that contains them in policy text."""
  text = json.dumps(record, ensure_ascii=False)
  for char, escaped in (("\u2028", "\\u2028"), ("\u2029", "\\u2029"), ("\x85", "\\u0085")):
    text = text.replace(char, escaped)
  return text + "\n"


def write_export(path: Path, text: str) -> Path:
  """Atomically write a derived export; if the file is locked (e.g. open in Excel) write ``*.pending``.

  Exports are rebuilt from metadata/ at any time, so a locked export must not abort a run.
  """
  try:
    atomic_write_text(path, text)
    path.with_name(f"{path.stem}.pending{path.suffix}").unlink(missing_ok=True)  # clear stale fallback
    return path
  except PermissionError:
    pending = path.with_name(f"{path.stem}.pending{path.suffix}")
    atomic_write_text(pending, text)
    logger.warning("%s is locked by another program; wrote %s instead. Close the file and re-run `report`.",
                   path.name, pending.name)
    return pending


def export_all(cfg: ScraperConfig, store: PolicyStore) -> dict[str, Path]:
  """Rebuild JSONL / CSV / failures from the per-company metadata (idempotent)."""
  records = store.all_records()
  _mark_duplicates(records)
  policies, failures = [], []
  for rec in records:
    if rec["scraping_status"] == "success":
      policies.append({**rec, "content": store.load_processed(rec)})
    else:
      failures.append(rec)
  paths = {
    "jsonl": cfg.data_dir / "fortune500_policies.jsonl",
    "csv": cfg.data_dir / "fortune500_policies_summary.csv",
    "failures": cfg.failures_dir / "fortune500_scraping_failures.jsonl",
  }
  paths["jsonl"] = write_export(paths["jsonl"], "".join(jsonl_line(p) for p in policies))
  paths["failures"] = write_export(paths["failures"], "".join(jsonl_line(f) for f in failures))
  buffer = io.StringIO(newline="")
  writer = csv.DictWriter(buffer, fieldnames=_SUMMARY_COLUMNS)
  writer.writeheader()
  for rec in records:
    row = {k: rec.get(k) for k in _SUMMARY_COLUMNS}
    row["redirect_hops"] = max(len(rec.get("redirect_chain") or []) - 1, 0)
    row["review_flags"] = ";".join(rec.get("review_flags") or [])
    row["quality_flags"] = ";".join(rec.get("quality_flags") or [])
    writer.writerow(row)
  paths["csv"] = write_export(paths["csv"], "﻿" + buffer.getvalue())  # BOM so Excel reads UTF-8
  return paths


def build_report(cfg: ScraperConfig, store: PolicyStore, rows: list[InputRow]) -> dict[str, Any]:
  """Exact data-quality counts (re-verifies every success against the quality checks)."""
  records = store.all_records()
  _mark_duplicates(records)
  by_status = Counter(r["scraping_status"] for r in records)
  success = [r for r in records if r["scraping_status"] == "success"]
  reverify_failures = []
  for rec in success:
    text = store.load_processed(rec)
    verdict = quality.assess(text, min_chars=cfg.min_chars, min_words=cfg.min_words)
    if not verdict.ok or content_hash(text) != rec["content_hash"]:
      reverify_failures.append({"company_id": rec["company_id"], "issues": verdict.issues})
  issue_counter = Counter(i.split(":")[0] for r in rows for i in r.issues)
  report = {
    "generated_at": _now(),
    "scraper": "scrapling",
    "scrapling_version": scrapling.__version__,
    "input": {
      "rows": len(rows),
      "fetchable": sum(r.fetchable for r in rows),
      "not_fetchable": sum(not r.fetchable for r in rows),
      "issue_counts": dict(issue_counter),
    },
    "attempted_records": len(records),
    "not_yet_attempted": len(rows) - len(records),
    "by_status": dict(by_status),
    "successful": len(success),
    "failed": by_status.get("failed", 0),
    "skipped": by_status.get("skipped", 0),
    "success_rate_of_fetchable": round(len(success) / max(sum(r.fetchable for r in rows), 1), 4),
    "by_document_type": dict(Counter(r.get("document_type") for r in success)),
    "by_tier": dict(Counter(r.get("scrape_tier") for r in success)),
    "redirected": sum(1 for r in records if len(r.get("redirect_chain") or []) > 1),
    "domain_changed": sum(1 for r in records if "domain_change" in (r.get("review_flags") or [])),
    "failure_stage_counts": dict(Counter(r.get("failure_stage") for r in records if r["scraping_status"] != "success")),
    "failure_kind_counts": dict(Counter(r.get("error_kind") for r in records if r["scraping_status"] != "success")),
    "quality": {
      "empty_content": sum(1 for r in success if r["content_length"] == 0),
      "suspiciously_short": sum(1 for r in success if r["content_length"] < 2000),
      "duplicate_content": sum(1 for r in success if r.get("duplicate_of")),
      "encoding_problems": sum(1 for r in records if "encoding_problem" in (r.get("quality_flags") or [])),
      "missing_company_metadata": sum(1 for r in records if not r.get("company_name") or not r.get("website")),
      "reverification_failures": reverify_failures,
      "corrupted_metadata_files": len(list(cfg.metadata_dir.glob("*.json"))) - len(records),
      "http_scheme_original_url": sum(1 for r in records if str(r.get("original_policy_url", "")).startswith("http://")),
    },
    "avg_elapsed_s": round(sum(r["elapsed_s"] for r in records) / max(len(records), 1), 2),
  }
  write_export(cfg.data_dir / "fortune500_scraping_report.json", json.dumps(report, indent=2, ensure_ascii=False))
  return report
