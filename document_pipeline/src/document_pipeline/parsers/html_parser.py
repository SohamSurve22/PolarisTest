"""HTML document parser."""

from html.parser import HTMLParser

from document_pipeline.core.exceptions import UnreadableDocumentError
from document_pipeline.parsers.base import BaseParser, ParseResult

_SKIP_TAGS = frozenset({"script", "style", "noscript", "template"})
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_BLOCK_TAGS = frozenset({
  "p",
  "div",
  "li",
  "tr",
  "section",
  "article",
  "header",
  "footer",
  "blockquote",
  "pre",
  "ul",
  "ol",
  "table",
  "thead",
  "tbody",
  "tfoot",
  "hr",
  "figure",
  "figcaption",
  "address",
})


class _HtmlTextExtractor(HTMLParser):
  """Collects visible text; converts headings to markdown hashes."""

  def __init__(self) -> None:
    super().__init__(convert_charrefs=True)
    self.chunks: list[str] = []
    self.title: str | None = None
    self._skip = 0
    self._in_title = False
    self._title_parts: list[str] = []
    self._heading_level: int | None = None
    self._heading_parts: list[str] = []

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    del attrs
    tag = tag.lower()
    if tag in _SKIP_TAGS:
      self._skip += 1
      return
    if self._skip:
      return
    if tag == "br":
      self.chunks.append("\n")
      return
    if tag == "title":
      self._in_title = True
      return
    if tag in _HEADING_TAGS:
      self._heading_level = int(tag[1])
      self._heading_parts = []
      self.chunks.append("\n")
      return
    if tag in _BLOCK_TAGS:
      self.chunks.append("\n")

  def handle_endtag(self, tag: str) -> None:
    tag = tag.lower()
    if tag in _SKIP_TAGS:
      if self._skip:
        self._skip -= 1
      return
    if self._skip:
      return
    if tag == "title":
      self._in_title = False
      title = " ".join("".join(self._title_parts).split())
      self.title = title or None
      return
    if tag in _HEADING_TAGS and self._heading_level is not None:
      body = " ".join("".join(self._heading_parts).split())
      if body:
        self.chunks.append(f"{'#' * self._heading_level} {body}\n")
      self._heading_level = None
      self._heading_parts = []
      return
    if tag in _BLOCK_TAGS:
      self.chunks.append("\n")

  def handle_data(self, data: str) -> None:
    if self._skip:
      return
    if self._in_title:
      self._title_parts.append(data)
      return
    if self._heading_level is not None:
      self._heading_parts.append(data)
      return
    self.chunks.append(data)


def _normalize_text(text: str) -> str:
  collapsed: list[str] = []
  blank = False
  for raw_line in text.splitlines():
    line = raw_line.strip()
    if not line:
      if collapsed and not blank:
        collapsed.append("")
      blank = True
      continue
    collapsed.append(line)
    blank = False
  return "\n".join(collapsed).strip()


class HtmlParser(BaseParser):
  """Extracts visible text from HTML without executing scripts."""

  def parse(self, data: bytes, *, encoding: str = "utf-8") -> ParseResult:
    try:
      html = data.decode(encoding)
    except UnicodeDecodeError as exc:
      msg = f"Failed to decode text document using encoding {encoding!r}"
      raise UnreadableDocumentError(msg) from exc

    extractor = _HtmlTextExtractor()
    extractor.feed(html)
    extractor.close()
    return ParseResult(
      raw_text=_normalize_text("".join(extractor.chunks)),
      title=extractor.title,
    )
