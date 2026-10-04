#!/usr/bin/env python3
"""Save Fortune 500 privacy-policy pages as PDFs.

Reads data/fortune500_policies/fortune500_policy_urls.csv and writes one PDF
per company under data/fortune500_policies/pdfs/. Pages that are already PDFs
are downloaded directly. HTML pages are printed with headless Chrome.

The run is resumable: a valid existing PDF is left in place.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "fortune500_policies" / "fortune500_policy_urls.csv"
DEFAULT_OUT = ROOT / "data" / "fortune500_policies" / "pdfs"
DEFAULT_MANIFEST = ROOT / "data" / "fortune500_policies" / "manifest.jsonl"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
CHROME_ERROR_MARKERS = (
    b"ERR_NAME_NOT_RESOLVED",
    b"ERR_CONNECTION_REFUSED",
    b"ERR_CONNECTION_TIMED_OUT",
    b"ERR_TIMED_OUT",
    b"ERR_SSL",
    b"ERR_CERT",
    b"ERR_TOO_MANY_REDIRECTS",
    b"ERR_EMPTY_RESPONSE",
    b"This site can\xe2\x80\x99t be reached",
    b"This site can't be reached",
)
BAD_PDF_TITLES = (
    b"page not found",
    b"access denied",
    b"just a moment",
    b"attention required",
    b"403 forbidden",
    b"404 not found",
)
MIN_PDF_BYTES = 8_000
_manifest_lock = threading.Lock()


def slug(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip()).strip("_")
    return (cleaned or "company")[:80]


def pdf_name(rank: str, company: str) -> str:
    return f"{int(rank):03d}_{slug(company)}.pdf"


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    cleaned: list[dict[str, str]] = []
    for row in rows:
        cleaned.append(
            {
                "company_name": (row.get("company_name") or "").strip(),
                "rank": (row.get("rank") or "").strip(),
                "website": (row.get("website") or "").strip(),
                "policy_url": (row.get("policy_url") or "").strip(),
            }
        )
    return cleaned


def is_valid_pdf(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < MIN_PDF_BYTES:
        return False
    try:
        with path.open("rb") as handle:
            header = handle.read(5)
            handle.seek(max(0, path.stat().st_size - 128))
            tail = handle.read()
    except OSError:
        return False
    if not header.startswith(b"%PDF") or b"%%EOF" not in tail:
        return False
    try:
        with path.open("rb") as handle:
            head = handle.read(32_000)
            handle.seek(max(0, path.stat().st_size - 16_000))
            trailer = handle.read()
    except OSError:
        return False
    sample = head + trailer
    if any(marker in sample for marker in CHROME_ERROR_MARKERS):
        return False
    title = re.search(br"/Title\s*\(([^)]*)\)", sample, re.IGNORECASE)
    if title and any(bad in title.group(1).lower() for bad in BAD_PDF_TITLES):
        return False
    return True


def append_manifest(path: Path, record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False)
    with _manifest_lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def download_if_pdf(url: str) -> tuple[str, bytes | None, str]:
    """Return (final_url, pdf_bytes_or_none, note)."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final = response.geturl()
            content_type = (response.headers.get("Content-Type") or "").lower()
            looks_pdf = "pdf" in content_type or final.lower().split("?", 1)[0].endswith(".pdf")
            if not looks_pdf:
                return final, None, f"html {response.status}"
            payload = response.read()
            if not payload.startswith(b"%PDF"):
                return final, None, "content-type pdf but body is not a pdf"
            return final, payload, f"downloaded pdf {response.status}"
    except urllib.error.HTTPError as exc:
        return url, None, f"http {exc.code}"
    except Exception as exc:  # noqa: BLE001 - record and fall through to Chrome
        return url, None, f"fetch failed: {exc.__class__.__name__}: {exc}"


def _drain(pipe, chunks: list[bytes]) -> None:
    try:
        chunks.append(pipe.read())
    except Exception:
        return


def _kill_group(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        return


def _pdf_size_stable(dest: Path, last_size: int) -> tuple[bool, int]:
    """Size-only check. Opening the file while Chrome holds it deadlocks."""
    if not dest.is_file():
        return False, last_size
    size = dest.stat().st_size
    return size >= MIN_PDF_BYTES and size == last_size, size


def print_with_chrome(url: str, dest: Path) -> str:
    """Print a page to PDF. Chrome often stays alive after the file is written."""
    if not CHROME.is_file():
        raise FileNotFoundError(f"Chrome not found at {CHROME}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    with tempfile.TemporaryDirectory(prefix="policy-chrome-") as profile:
        cmd = [
            str(CHROME),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--use-mock-keychain",
            "--password-store=basic",
            f"--user-data-dir={profile}",
            "--virtual-time-budget=12000",
            "--no-pdf-header-footer",
            f"--print-to-pdf={dest}",
            url,
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        threading.Thread(target=_drain, args=(proc.stdout, stdout_chunks), daemon=True).start()
        threading.Thread(target=_drain, args=(proc.stderr, stderr_chunks), daemon=True).start()
        deadline = time.monotonic() + 45
        last_size = -1
        stable_since: float | None = None
        try:
            while time.monotonic() < deadline:
                stable, last_size = _pdf_size_stable(dest, last_size)
                if stable:
                    if stable_since is None:
                        stable_since = time.monotonic()
                    elif time.monotonic() - stable_since >= 1.0:
                        break
                else:
                    stable_since = None
                if proc.poll() is not None and dest.is_file() and dest.stat().st_size >= MIN_PDF_BYTES:
                    break
                if proc.poll() is not None and not dest.is_file():
                    break
                time.sleep(0.25)
            else:
                raise TimeoutError("chrome timed out before a pdf was written")
        finally:
            _kill_group(proc)
        if not is_valid_pdf(dest):
            err = b"".join(stderr_chunks).decode("utf-8", "replace")[-400:].strip()
            raise RuntimeError(err or f"chrome exit {proc.returncode}")
    return "printed with chrome"


def scrape_one(row: dict[str, str], out_dir: Path, manifest: Path) -> dict:
    rank = row["rank"]
    company = row["company_name"]
    url = row["policy_url"]
    dest = out_dir / pdf_name(rank, company)
    record = {
        "rank": rank,
        "company_name": company,
        "policy_url": url,
        "pdf": str(dest.relative_to(ROOT)),
        "status": "failed",
        "bytes": 0,
        "detail": "",
    }
    if not url or url.lower() == "none":
        record["detail"] = "missing policy_url"
        record["pdf"] = ""
        append_manifest(manifest, record)
        return record
    if is_valid_pdf(dest):
        record["status"] = "skipped"
        record["bytes"] = dest.stat().st_size
        record["detail"] = "already saved"
        append_manifest(manifest, record)
        return record

    final, pdf_bytes, note = download_if_pdf(url)
    record["final_url"] = final
    try:
        if pdf_bytes is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(pdf_bytes)
            record["detail"] = note
        else:
            record["detail"] = print_with_chrome(final or url, dest)
            if note.startswith("http ") or note.startswith("fetch failed"):
                record["detail"] = f"{record['detail']} after {note}"
        if not is_valid_pdf(dest):
            size = dest.stat().st_size if dest.is_file() else 0
            record["bytes"] = size
            record["detail"] = f"invalid pdf ({size} bytes); {record['detail']}"
            if dest.is_file():
                dest.unlink()
            record["pdf"] = ""
        else:
            record["status"] = "ok"
            record["bytes"] = dest.stat().st_size
    except Exception as exc:  # noqa: BLE001 - one bad site must not stop the batch
        record["detail"] = f"{note}; {exc.__class__.__name__}: {exc}"
        record["pdf"] = ""
        if dest.is_file() and not is_valid_pdf(dest):
            dest.unlink()
    append_manifest(manifest, record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0, help="Scrape only the first N rows")
    args = parser.parse_args()

    if shutil.which(str(CHROME)) is None and not CHROME.is_file():
        raise SystemExit(f"Google Chrome is required at {CHROME}")

    rows = load_rows(args.csv)
    if args.limit:
        rows = rows[: args.limit]
    args.out.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    ok = skipped = failed = 0
    print(f"scraping {len(rows)} policies with {args.workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(scrape_one, row, args.out, args.manifest) for row in rows]
        for index, future in enumerate(as_completed(futures), start=1):
            record = future.result()
            if record["status"] == "ok":
                ok += 1
            elif record["status"] == "skipped":
                skipped += 1
            else:
                failed += 1
            print(
                f"[{index}/{len(rows)}] {record['status']:7} "
                f"{record['rank']:>3} {record['company_name']} "
                f"({record['bytes']} bytes) {record['detail']}",
                flush=True,
            )
    print(f"done ok={ok} skipped={skipped} failed={failed}", flush=True)


if __name__ == "__main__":
    main()
