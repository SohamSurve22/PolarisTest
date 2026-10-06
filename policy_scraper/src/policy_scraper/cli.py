"""policy-scraper CLI: scrape | report | inspect-input."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from policy_scraper.config import PACKAGE_ROOT, ScraperConfig
from policy_scraper.urls import load_rows

DEFAULT_INPUT = PACKAGE_ROOT / "data" / "input" / "fortune500_policy_urls.csv"


def _config_from(args: argparse.Namespace) -> ScraperConfig:
  cfg = ScraperConfig()
  if getattr(args, "output", None):
    cfg.data_dir = Path(args.output).resolve()
  if getattr(args, "max_concurrency", None):
    cfg.max_concurrency = args.max_concurrency
  if getattr(args, "delay", None) is not None:
    cfg.domain_delay_s = args.delay
  if getattr(args, "tiers", None):
    cfg.tiers = tuple(t.strip() for t in args.tiers.split(",") if t.strip())
  if getattr(args, "allow_stealth", False):
    cfg.allow_stealth = True
  return cfg


def _setup_logging(verbose: bool) -> None:
  logging.basicConfig(
    level=logging.DEBUG if verbose else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
  )
  logging.getLogger("scrapling").setLevel(logging.WARNING)
  logging.getLogger("urllib3").setLevel(logging.WARNING)


def _retry_kinds(args: argparse.Namespace) -> tuple[str, ...]:
  from policy_scraper.scrape import TRANSIENT_KINDS

  if args.retry_transient:
    return TRANSIENT_KINDS
  return tuple(k.strip() for k in (args.retry_kind or "").split(",") if k.strip())


def cmd_scrape(args: argparse.Namespace) -> int:
  from policy_scraper.scrape import build_report, pending_rows, run_batch
  from policy_scraper.store import PolicyStore

  cfg = _config_from(args)
  rows = load_rows(Path(args.input))
  store = PolicyStore(cfg)
  todo = pending_rows(
    rows, store, retry_failed=args.retry_failed, force=args.force,
    company=args.company, start_index=args.start_index, limit=args.limit,
    retry_kinds=_retry_kinds(args),
  )
  logging.info("input rows=%d selected=%d (resume skips already-scraped rows)", len(rows), len(todo))
  if todo:
    run_batch(todo, cfg, store)
  report = build_report(cfg, store, rows)
  print(json.dumps({k: report[k] for k in ("attempted_records", "by_status", "not_yet_attempted")}, indent=2))
  return 0


def cmd_report(args: argparse.Namespace) -> int:
  from policy_scraper.scrape import build_report, export_all
  from policy_scraper.store import PolicyStore

  cfg = _config_from(args)
  store = PolicyStore(cfg)
  export_all(cfg, store)
  print(json.dumps(build_report(cfg, store, load_rows(Path(args.input))), indent=2))
  return 0


def cmd_inspect_input(args: argparse.Namespace) -> int:
  from collections import Counter

  rows = load_rows(Path(args.input))
  counts = Counter(i.split(":")[0] for r in rows for i in r.issues)
  print(json.dumps({"rows": len(rows), "fetchable": sum(r.fetchable for r in rows), "issues": dict(counts)}, indent=2))
  for row in rows:
    if row.issues and args.verbose:
      print(row.company_id, row.issues)
  return 0


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(prog="policy-scraper")
  p.add_argument("-v", "--verbose", action="store_true")
  sub = p.add_subparsers(dest="command", required=True)

  def common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--input", default=str(DEFAULT_INPUT), help="CSV of company policy URLs")
    sp.add_argument("--output", help="data directory (default: policy_scraper/data/policies)")

  sc = sub.add_parser("scrape", help="scrape policies with Scrapling (resumable)")
  common(sc)
  sc.add_argument("--limit", type=int)
  sc.add_argument("--start-index", type=int, default=0)
  sc.add_argument("--resume", action="store_true", help="skip already-scraped rows (default behaviour)")
  sc.add_argument("--retry-failed", action="store_true", help="only re-attempt rows whose last status is failed")
  sc.add_argument("--retry-kind", help="with --retry-failed: only error_kind prefixes (comma list)")
  sc.add_argument("--retry-transient", action="store_true", help="with --retry-failed: only transient network failures")
  sc.add_argument("--force", action="store_true", help="re-scrape everything selected, even successes")
  sc.add_argument("--company", help="company name substring or company_id")
  sc.add_argument("--max-concurrency", type=int)
  sc.add_argument("--delay", type=float, help="minimum seconds between requests to the same host")
  sc.add_argument("--tiers", help="comma list, default http,dynamic")
  sc.add_argument("--allow-stealth", action="store_true", help="enable Scrapling StealthyFetcher as last resort")
  sc.set_defaults(handler=cmd_scrape)

  rp = sub.add_parser("report", help="rebuild exports and print the data-quality report")
  common(rp)
  rp.set_defaults(handler=cmd_report)

  ii = sub.add_parser("inspect-input", help="validate the CSV without scraping")
  common(ii)
  ii.set_defaults(handler=cmd_inspect_input)

  return p


def main(argv: list[str] | None = None) -> int:
  args = build_parser().parse_args(argv)
  _setup_logging(args.verbose)
  try:
    return int(args.handler(args))
  except KeyboardInterrupt:
    logging.warning("interrupted; per-company state is saved, re-run to resume")
    return 130


if __name__ == "__main__":
  sys.exit(main())
