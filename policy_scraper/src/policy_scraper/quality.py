"""Content-quality verdicts: an HTTP 200 is never proof that policy text was extracted."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

_POLICY_TERMS = (
  "privacy", "personal information", "personal data", "collect", "cookies", "share",
  "disclose", "third part", "retain", "retention", "your rights", "opt out", "opt-out",
  "terms", "disclaimer", "liability", "use of this", "consent", "security", "contact us",
  "legal", "information we", "data protection", "affiliates", "service provider",
)
_BLOCK_PHRASES = (
  "access denied", "request blocked", "are you a robot", "unusual traffic",
  "pardon our interruption", "verify you are human", "enable javascript", "checking your browser",
  "attention required", "please enable cookies", "bot detection", "captcha",
  "403 forbidden", "you have been blocked",
)
_NOT_FOUND = ("page not found", "404 not found", "404 error", "this page can't be found",
              "we couldn't find that page", "page cannot be found", "no longer available")
_LOGIN_PATH = re.compile(r"(^|/)(login|signin|sign-in|sso|auth|authenticate|account/login|logon)(/|$|\.)", re.I)
_MOJIBAKE = re.compile(r"(Ã.|â€.|Â )")


@dataclass
class Verdict:
  ok: bool
  issues: list[str] = field(default_factory=list)
  policy_terms_found: int = 0
  words: int = 0

  @property
  def needs_rendering(self) -> bool:
    """True if the content shape suggests JS-rendered or blocked output (try a browser)."""
    return any(i in self.issues for i in ("empty", "too_short", "blocked_page", "js_required"))


def assess(
  text: str,
  *,
  min_chars: int,
  min_words: int,
  has_noscript: bool = False,
  title: str = "",
) -> Verdict:
  issues: list[str] = []
  stripped = text.strip()
  words = len(stripped.split())
  low = stripped.lower()
  if not stripped:
    issues.append("empty")
  elif len(stripped) < min_chars or words < min_words:
    issues.append("too_short")
  head = f"{title.lower()} {low[:1500]}"
  if any(p in head for p in _BLOCK_PHRASES) and words < 600:
    issues.append("blocked_page")
  if any(p in head for p in _NOT_FOUND) and words < 600:
    issues.append("error_page")
  if has_noscript and ("empty" in issues or "too_short" in issues):
    issues.append("js_required")
  if stripped:
    if stripped.count("�") > 5 or len(_MOJIBAKE.findall(stripped)) > 5:
      issues.append("encoding_problem")
    alpha = sum(c.isalpha() for c in stripped)
    if alpha / max(len(stripped), 1) < 0.5:
      issues.append("low_alpha_ratio")
  terms = sum(1 for t in _POLICY_TERMS if t in low)
  if stripped and terms < 3:
    issues.append("no_policy_language")
  return Verdict(ok=not issues, issues=issues, policy_terms_found=terms, words=words)


def review_redirect(original: str, final: str) -> list[str]:
  """Flags for redirects that need human review. Never blindly accepted."""
  from tld import get_fld

  flags: list[str] = []
  if original == final:
    return flags
  o, f = urlsplit(original), urlsplit(final)

  def fld(host: str | None) -> str:
    try:
      return get_fld(f"https://{host}", fail_silently=True) or (host or "")
    except Exception:
      return host or ""

  if fld(o.hostname) != fld(f.hostname):
    flags.append("domain_change")
  if _LOGIN_PATH.search(f.path) and not _LOGIN_PATH.search(o.path):
    flags.append("redirect_to_login")
  if f.path in ("", "/") and o.path not in ("", "/"):
    flags.append("redirect_to_homepage")
  return flags
