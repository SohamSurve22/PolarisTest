# policy_scraper

Resumable scraper for corporate privacy and legal policies, built on
[Scrapling](https://github.com/D4Vinci/Scrapling). It reads a CSV of companies and policy URLs and produces a
structured dataset (raw files, cleaned text, per-company metadata, JSONL/CSV exports, a quality report).
It is a self-contained add-on: it has its own virtual environment and data folder, and PolarisLex only
contributes its PDF parser (`document_pipeline`).

## How it works

1. **Input** – the CSV is read dynamically and every row is validated (missing/invalid URLs, duplicates,
   http vs https). Nothing is dropped silently; unusable rows are recorded as `skipped`.
2. **robots.txt** – respected (RFC 9309). Lookups are retried; a robots.txt that stays unreachable means
   "deny". A per-host delay is enforced.
3. **Fetch with fallback** – `Fetcher` (HTTP) → `DynamicFetcher` (Chromium, for JS pages, WAF-style 404s and
   403s) → `StealthyFetcher` (opt-in via `--allow-stealth`, never solves CAPTCHAs). Blocked sites are
   recorded as failures, not retried indefinitely.
4. **Redirects** – followed (max 10) and recorded as a chain. Loops, redirects to login pages and redirects to
   a site homepage are rejected; cross-domain redirects are kept and flagged `domain_change`.
5. **Extract** – HTML: main content only (navigation, footers, banners, scripts removed), headings kept as
   `#` markdown. PDF: text extracted with the existing PolarisLex PDF parser. Whitespace is normalised and
   repeated nav-style lines are collapsed.
6. **Quality gate** – an HTTP 200 is not success. Text must pass length, policy-vocabulary, block-page,
   error-page and encoding checks, otherwise the record is `failed` with the reason.
7. **Persist** – each company is written atomically as soon as it finishes, so runs can be interrupted,
   resumed, or retried safely.

## Install

```powershell
cd policy_scraper
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ..\document_pipeline
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\scrapling install        # downloads Chromium for the dynamic/stealth tiers
```

Default input: `data/input/fortune500_policy_urls.csv` (columns `company_name, rank, website, policy_url`).

## Usage

```powershell
$ps = ".\.venv\Scripts\policy-scraper"
& $ps inspect-input                          # validate the CSV only
& $ps scrape --limit 25                      # first 25 not-yet-scraped rows
& $ps scrape --allow-stealth                 # all rows; already-scraped rows are skipped (resume)
& $ps scrape --retry-failed                  # re-attempt rows whose last status was failed
& $ps scrape --retry-failed --retry-transient   # only DNS/timeout/5xx/rate-limit failures
& $ps scrape --company "Sysco" --force       # re-scrape one company
& $ps scrape --start-index 100 --limit 50 --max-concurrency 4 --delay 3
& $ps report                                 # rebuild exports and print the quality report
```

Options: `--input`, `--output`, `--limit`, `--start-index`, `--resume`, `--retry-failed`,
`--retry-kind`, `--retry-transient`, `--force`, `--company`, `--max-concurrency`, `--delay`, `--tiers`,
`--allow-stealth`. Safe to Ctrl+C; exports are rebuilt on exit.

## Output (`data/policies/`)

| Path | Content |
|---|---|
| `raw/<id>.html` / `.pdf` | bytes exactly as fetched |
| `processed/<id>.txt` | cleaned policy text with `#` headings |
| `metadata/<id>.json` | one record per company (source of truth) |
| `fortune500_policies.jsonl` | successful records including `content` |
| `fortune500_policies_summary.csv` | one row per company, no bodies |
| `fortune500_scraping_report.json` | data-quality counts |
| `failures/fortune500_scraping_failures.jsonl` | failed and skipped records |

`<id>` is `<rank>-<company-slug>` (deterministic). Each record holds: company name, rank, website, original
and final URL, redirect chain, document type, status, failure stage and error kind, HTTP status, content type,
title, content length, word count, SHA-256 content hash, tiers attempted, quality and review flags,
robots.txt result, input issues, timestamp, scraper and version.

## Tests

```powershell
.\.venv\Scripts\python -m pytest -q          # mocked HTTP only, no network
```
