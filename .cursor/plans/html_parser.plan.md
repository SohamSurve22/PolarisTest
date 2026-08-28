---
name: HTML parser
overview: "Add HtmlParser using stdlib html.parser, wire .html/.htm into DocumentLoader and preview CLI. No BeautifulSoup. SQLite stays parked."
todos:
  - id: html-parser
    content: HtmlParser strips tags/scripts, emits markdown hashes for h1-h6, title from <title>
    status: completed
  - id: loader-cli
    content: Register .html/.htm on DocumentLoader and preview CLI
    status: completed
  - id: tests
    content: Parser + loader + preview tests (no reportlab)
    status: completed
isProject: true
---

# HTML parser

**Goal:** Load scraped policy HTML the same way as txt/pdf/docx.

**Architecture:** `HtmlParser(BaseParser)` via stdlib `html.parser`. Block tags become newlines; `h1`–`h6` become markdown `#` lines so `HeadingDetector` can see them. Skip `script`/`style`/`noscript`. Decode like `TxtParser`.

**Out of scope:** SQLite, BeautifulSoup, JS-rendered pages.
