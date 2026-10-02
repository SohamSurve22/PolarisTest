from pathlib import Path

import pytest

from policy_scraper import quality
from policy_scraper.urls import load_rows, make_company_id, validate_url

CSV = (
  "company_name,rank,website,policy_url\n"
  'Walmart ,1,http://www.walmart.com,"https://corp.walmart.com/privacy\n"\n'
  "Apple ,2,http://www.apple.com,http://www.apple.com/privacy/\n"
  "Genuine Parts ,3,http://www.gp.com,None\n"
  "Bad Scheme,4,http://x.com,ftp://x.com/p\n"
  "Dup Url,5,http://dup.com,https://www.apple.com/privacy\n"
  ",6,http://noname.com,https://noname.com/privacy\n"
  "Apple ,7,http://www.apple.com,https://apple.com/other\n"
  "Cisco ,8,http://cisco.com,http://www.cisco.com//www.cisco.com/c/privacy\n"
)


def _rows(tmp_path: Path):
  path = tmp_path / "in.csv"
  path.write_text(CSV, encoding="utf-8")
  return load_rows(path)


def test_embedded_newline_and_trailing_space_cleaned(tmp_path: Path) -> None:
  rows = _rows(tmp_path)
  assert rows[0].company_name == "Walmart"
  assert rows[0].policy_url == "https://corp.walmart.com/privacy"


def test_missing_and_invalid_urls_are_kept_not_dropped(tmp_path: Path) -> None:
  rows = _rows(tmp_path)
  assert len(rows) == 8
  assert not rows[2].fetchable and "missing_policy_url" in rows[2].issues
  assert not rows[3].fetchable and "invalid_url_scheme" in rows[3].issues


def test_duplicates_and_missing_name_flagged(tmp_path: Path) -> None:
  rows = _rows(tmp_path)
  assert any(i.startswith("duplicate_url:") for i in rows[4].issues)
  assert "missing_company_name" in rows[5].issues
  assert any(i.startswith("duplicate_company:") for i in rows[6].issues)
  assert "malformed_double_slash_path" in rows[7].issues
  assert "http_scheme" in rows[1].issues


def test_company_ids_deterministic_and_unique(tmp_path: Path) -> None:
  a, b = _rows(tmp_path), _rows(tmp_path)
  assert [r.company_id for r in a] == [r.company_id for r in b]
  assert len({r.company_id for r in a}) == len(a)
  assert make_company_id(1, "Johnson & Johnson", 1) == "001-johnson-and-johnson"


def test_missing_required_column_raises(tmp_path: Path) -> None:
  path = tmp_path / "bad.csv"
  path.write_text("company_name,rank\nA,1\n", encoding="utf-8")
  with pytest.raises(ValueError):
    load_rows(path)


@pytest.mark.parametrize("raw,ok", [("none", False), ("", False), ("https://a.com/x", True), ("mailto:a@b.c", False), ("http://localhost/x", False)])
def test_validate_url(raw: str, ok: bool) -> None:
  assert bool(validate_url(raw)[0]) is ok


def test_redirect_review_flags() -> None:
  assert quality.review_redirect("https://a.com/privacy", "https://a.com/privacy") == []
  assert "domain_change" in quality.review_redirect("https://a.com/privacy", "https://other.org/privacy")
  assert "redirect_to_login" in quality.review_redirect("https://a.com/privacy", "https://a.com/login?next=x")
  assert "redirect_to_homepage" in quality.review_redirect("https://a.com/privacy", "https://a.com/")
  # same registrable domain, different subdomain is not a domain change
  assert "domain_change" not in quality.review_redirect("https://www.a.com/p", "https://corp.a.com/p")


POLICY = ("We collect personal information and cookies. We share data with third parties and service providers. "
          "You have rights to opt out. Contact us about privacy. We retain data and apply security measures. ") * 12


def test_assess_accepts_real_policy() -> None:
  v = quality.assess(POLICY, min_chars=800, min_words=120)
  assert v.ok, v.issues


def test_assess_rejects_empty_short_blocked_and_nonpolicy() -> None:
  assert "empty" in quality.assess("", min_chars=800, min_words=120).issues
  assert "too_short" in quality.assess("Privacy policy", min_chars=800, min_words=120).issues
  blocked = "Access Denied. " + POLICY[:300]
  assert "blocked_page" in quality.assess(blocked, min_chars=100, min_words=20).issues
  filler = "lorem ipsum dolor sit amet " * 100
  assert "no_policy_language" in quality.assess(filler, min_chars=800, min_words=120).issues


def test_assess_flags_js_required_and_mojibake() -> None:
  v = quality.assess("", min_chars=800, min_words=120, has_noscript=True)
  assert "js_required" in v.issues and v.needs_rendering
  garbled = ("Ã©Ã¨ " * 20 + POLICY)
  assert "encoding_problem" in quality.assess(garbled, min_chars=100, min_words=20).issues
