"""Policy content extraction: HTML main-content (via Scrapling's parser) and PDF text."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from scrapling.parser import Selector

_DROP_TAGS = {
  "script", "style", "noscript", "template", "svg", "iframe", "canvas", "form",
  "nav", "footer", "aside", "button", "select", "input", "dialog", "head",
}
_ALWAYS_DROP = {"script", "style", "noscript", "template", "svg", "iframe", "canvas", "head"}
_HEADING = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_BLOCK = {
  "p", "div", "section", "article", "main", "header", "blockquote", "pre", "ul", "ol",
  "table", "thead", "tbody", "tr", "figure", "figcaption", "address", "dl", "dt", "dd",
  "details", "summary", "fieldset", "body", "html",
}
# Class / id fragments of non-content widgets. Matched on whole tokens to avoid
# dropping e.g. "cookie-policy-content".
_NOISE_TOKENS = re.compile(
  r"(^|[-_\s])(cookie-?banner|cookie-?consent|cookiebar|cc-window|onetrust-[a-z-]+|ot-sdk-[a-z-]+|"
  r"truste[a-z-]*|gdpr-banner|consent-banner|skip-?links?|breadcrumbs?|"
  r"site-?header|site-?footer|global-?footer|global-?header|megamenu|mega-menu|"
  r"newsletter|social-?share|back-to-top)($|[-_\s])",
  re.I,
)
_CANDIDATES = (
  "main", "[role=main]", "article", "#main-content", "#maincontent", "#main", "#content",
  ".main-content", ".page-content", ".content", ".policy-content", ".privacy-policy",
  "#privacy-policy", "#policy",
)
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)


@dataclass
class ExtractedContent:
  title: str
  text: str
  selector_used: str
  body_chars: int
  flags: list[str] = field(default_factory=list)


def decode_html(body: bytes, declared_encoding: str | None) -> str:
  """Decode bytes, preferring declared encoding, then utf-8, then cp1252 (lossless-ish)."""
  for enc in (declared_encoding, "utf-8"):
    if not enc:
      continue
    try:
      return body.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return body.decode("cp1252", errors="replace")


def normalize_text(text: str) -> str:
  """Normalise whitespace and unicode without altering wording."""
  text = unicodedata.normalize("NFC", text).translate(_ZERO_WIDTH)
  text = text.replace(" ", " ").replace("\r\n", "\n").replace("\r", "\n")
  lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.split("\n")]
  out: list[str] = []
  blank = 0
  for line in lines:
    if not line:
      blank += 1
      if blank == 1 and out:
        out.append("")
      continue
    blank = 0
    out.append(line)
  return "\n".join(out).strip()


def dedupe_repeated_lines(text: str, *, max_repeats: int = 3, min_len: int = 12, max_len: int = 120) -> str:
  """Drop consecutive duplicate lines, and short nav-like lines repeated more than ``max_repeats`` times.

  Only lines with ``min_len <= len <= max_len`` are collapsed so long legal paragraphs and tiny
  table cells (\"Yes\") are never removed by the repetition rule.
  """
  lines = text.split("\n")
  counts: dict[str, int] = {}
  for line in lines:
    if line:
      counts[line] = counts.get(line, 0) + 1
  out: list[str] = []
  previous = None
  seen: dict[str, int] = {}
  for line in lines:
    if line and line == previous:
      continue
    previous = line
    if line and min_len <= len(line) <= max_len and counts[line] > max_repeats:
      seen[line] = seen.get(line, 0) + 1
      if seen[line] > 1:
        continue
    out.append(line)
  return normalize_text("\n".join(out))


def _is_noise(el: object) -> bool:
  attrs = getattr(el, "attrib", {}) or {}
  if "hidden" in attrs or attrs.get("aria-hidden") == "true":
    return True
  style = (attrs.get("style") or "").replace(" ", "").lower()
  if "display:none" in style or "visibility:hidden" in style:
    return True
  marker = f"{attrs.get('class', '')} {attrs.get('id', '')}"
  role = attrs.get("role", "")
  return bool(_NOISE_TOKENS.search(marker)) or role in {"navigation", "banner", "contentinfo", "dialog"}


def _strip_noise(root: object) -> None:
  """Remove chrome (nav, footer, banners, scripts) without ever deleting the main content.

  Guards learned from real pages: ASP.NET wraps the whole page in one <form>, and Adobe
  Experience Manager uses ``cmp-container`` classes for content, so any non-script element
  holding a large share of the page text is kept and only its noisy descendants are removed.
  """
  total = _text_len(root)
  for el in list(root.iter()):  # type: ignore[attr-defined]
    tag = el.tag if isinstance(el.tag, str) else None
    if tag is None:  # comment / processing instruction
      _drop_keep_tail(el)
      continue
    if el.getparent() is None:
      continue
    low = tag.lower()
    if low in {"main", "article"}:
      continue
    if low in _ALWAYS_DROP:
      _drop_keep_tail(el)
      continue
    if low in _DROP_TAGS or _is_noise(el):
      if total and _text_len(el) > 0.4 * total:
        continue
      _drop_keep_tail(el)


def _drop_keep_tail(el: object) -> None:
  parent = el.getparent()  # type: ignore[attr-defined]
  if parent is None:
    return
  tail = el.tail  # type: ignore[attr-defined]
  prev = el.getprevious()  # type: ignore[attr-defined]
  if tail:
    if prev is not None:
      prev.tail = (prev.tail or "") + tail
    else:
      parent.text = (parent.text or "") + tail
  parent.remove(el)


def _walk(el: object, out: list[str]) -> None:
  tag = el.tag.lower() if isinstance(el.tag, str) else ""  # type: ignore[attr-defined]
  if tag in _HEADING:
    heading = " ".join("".join(el.itertext()).split())  # type: ignore[attr-defined]
    if heading:
      out.append(f"\n\n{'#' * _HEADING[tag]} {heading}\n\n")
    if el.tail:  # type: ignore[attr-defined]
      out.append(el.tail)  # type: ignore[attr-defined]
    return
  if tag == "br":
    out.append("\n")
  elif tag == "li":
    out.append("\n- ")
  elif tag in {"td", "th"}:
    out.append(" | ")
  elif tag in _BLOCK:
    out.append("\n\n" if tag in {"p", "section", "article", "table", "ul", "ol", "blockquote"} else "\n")
  if el.text:  # type: ignore[attr-defined]
    out.append(el.text)  # type: ignore[attr-defined]
  for child in el:  # type: ignore[attr-defined]
    if isinstance(child.tag, str):
      _walk(child, out)
    elif child.tail:
      out.append(child.tail)
  if tag in _BLOCK or tag == "li":
    out.append("\n")
  if el.tail:  # type: ignore[attr-defined]
    out.append(el.tail)  # type: ignore[attr-defined]


def _render(root: object) -> str:
  parts: list[str] = []
  # Render children only so the root's own tail (outside the element) is excluded.
  saved_tail = root.tail  # type: ignore[attr-defined]
  root.tail = None  # type: ignore[attr-defined]
  try:
    _walk(root, parts)
  finally:
    root.tail = saved_tail  # type: ignore[attr-defined]
  text = normalize_text("".join(parts))
  text = re.sub(r"\n\s*\|\s*\n", "\n", text)
  return dedupe_repeated_lines(text)


def _text_len(el: object) -> int:
  return len(" ".join("".join(el.itertext()).split()))  # type: ignore[attr-defined]


def _link_density(el: object) -> float:
  total = _text_len(el)
  if not total:
    return 1.0
  links = sum(_text_len(a) for a in el.iter("a"))  # type: ignore[attr-defined]
  return links / total


def extract_html(html: str, *, url: str = "") -> ExtractedContent:
  """Extract the primary policy text from an HTML document, keeping heading structure."""
  page = Selector(html, url=url) if url else Selector(html)
  title = (page.css("title::text").get() or "").strip()
  if not title:
    title = (page.css("h1::text").get() or "").strip()
  root = page._root  # lxml tree owned by the Scrapling Selector
  body_el = root.find(".//body")
  if body_el is None:
    body_el = root
  flags: list[str] = []
  if root.find(".//noscript") is not None:
    flags.append("has_noscript")
  _strip_noise(body_el)
  body_len = _text_len(body_el)

  chosen = body_el
  used = "body"
  best_len = 0
  for css in _CANDIDATES:
    try:
      found = page.css(css)
    except Exception:  # invalid selector for this document
      continue
    for node in found:
      el = node._root
      if el is body_el or not isinstance(el.tag, str):
        continue
      length = _text_len(el)
      if length > best_len and _link_density(el) < 0.5:
        best_len, chosen, used = length, el, css
  # Prefer the container only if it holds the bulk of the page text.
  if used != "body" and best_len < 0.6 * body_len:
    chosen, used = body_el, "body"
    flags.append("candidate_too_small_used_body")
  text = _render(chosen)
  return ExtractedContent(
    title=" ".join(title.split()),
    text=text,
    selector_used=used,
    body_chars=body_len,
    flags=flags,
  )


def extract_pdf(body: bytes) -> tuple[str, int | None, str | None, list[str]]:
  """Extract PDF text with the existing PolarisLex PDF parser (no HTML parsing of binaries)."""
  from document_pipeline.parsers.pdf_parser import PdfParser

  result = PdfParser().parse(body)
  text = normalize_text(result.raw_text)
  return text, result.page_count, result.title, list(result.extraction_notes)
