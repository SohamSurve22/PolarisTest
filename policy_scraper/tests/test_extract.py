from policy_scraper.extract import dedupe_repeated_lines, extract_html, normalize_text

PAGE = """<html><head><title>Acme Privacy Notice</title><style>.x{}</style></head><body>
<header><nav><a href="/">Home</a><a href="/jobs">Jobs</a></nav></header>
<div id="onetrust-banner-sdk">We use cookies. Accept all</div>
<main>
<h1>Privacy Notice</h1>
<p>We collect personal information when you visit.&nbsp;&nbsp;We share it   with partners.</p>
<h2>Your Rights</h2>
<ul><li>Access</li><li>Deletion</li></ul>
<p style="display:none">hidden tracking text</p>
<script>var tracking = 1;</script>
</main>
<footer>Copyright Acme. All rights reserved. Careers</footer>
</body></html>"""


def test_html_extraction_keeps_policy_removes_chrome() -> None:
  out = extract_html(PAGE, url="https://acme.test/privacy")
  assert out.title == "Acme Privacy Notice"
  assert "# Privacy Notice" in out.text
  assert "## Your Rights" in out.text
  assert "- Access" in out.text and "- Deletion" in out.text
  assert "We share it with partners." in out.text  # whitespace normalised, wording intact
  for junk in ("Careers", "Accept all", "hidden tracking", "var tracking", "Home"):
    assert junk not in out.text
  assert out.selector_used == "main"


def test_small_candidate_falls_back_to_body() -> None:
  html = ("<html><body><main><p>tiny</p></main><div>" + "<p>Long policy paragraph about data we collect. </p>" * 40
          + "</div></body></html>")
  out = extract_html(html)
  assert out.selector_used == "body"
  assert "Long policy paragraph" in out.text


def test_noscript_flag_and_empty_body() -> None:
  out = extract_html("<html><body><noscript>Enable JS</noscript><div id=root></div></body></html>")
  assert out.text == "" and "has_noscript" in out.flags


def test_normalize_text_preserves_words() -> None:
  assert normalize_text("a  b​\r\n\r\n\r\n c \t d") == "a b\n\nc d"


def test_dedupe_repeated_lines() -> None:
  text = "\n".join(["Menu item"] * 6 + ["Real paragraph", "Real paragraph", "Other"])
  out = dedupe_repeated_lines(text, max_repeats=3)
  assert out.count("Menu item") == 1
  assert out.count("Real paragraph") == 1 and "Other" in out


def test_dedupe_keeps_long_paragraphs_and_short_cells() -> None:
  para = "This long legal paragraph is intentionally repeated verbatim in the source document text. " * 2
  text = "\n".join([para.strip()] * 5 + ["Yes"] * 6)
  out = dedupe_repeated_lines(text, max_repeats=3)
  assert out.count("This long legal paragraph") >= 1 and out.count("Yes") >= 1
  assert out.splitlines().count(para.strip()) == 1  # consecutive duplicates still collapse


def _long(n: int = 30) -> str:
  return "".join(f"<p>Section {i}: we collect personal information and share it with service providers.</p>" for i in range(n))


def test_aem_cmp_container_classes_are_not_noise() -> None:
  html = f'<html><body><div class="cmp-container"><div class="cmp-text">{_long()}</div></div></body></html>'
  assert "Section 29" in extract_html(html).text


def test_aspnet_form_wrapper_is_not_dropped() -> None:
  html = f'<html><body><form id="aspnetForm"><nav>Menu</nav><h1>Policy</h1>{_long()}</form></body></html>'
  out = extract_html(html).text
  assert "Section 29" in out and "# Policy" in out and "Menu" not in out


def test_small_form_and_cookie_widget_still_removed() -> None:
  html = (f'<html><body><main>{_long()}</main><form><p>Subscribe to our newsletter for updates today</p>'
          '<input></form><div class="cookie-banner">Accept cookies</div></body></html>')
  out = extract_html(html).text
  assert "Subscribe" not in out and "Accept cookies" not in out and "Section 5" in out
