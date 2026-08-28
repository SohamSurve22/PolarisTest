from pathlib import Path

import pytest

from document_pipeline.core.exceptions import UnreadableDocumentError
from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.parsers.html_parser import HtmlParser
from document_pipeline.pipeline.stages.loader import DocumentLoader


def _source(path: Path) -> DocumentSource:
  return DocumentSource(
    metadata=DocumentMetadata(
      document_id="doc-html-001",
      filename=path.name,
      format=DocumentFormat.UNKNOWN,
      source_path=str(path),
    )
  )


def test_html_parser_extracts_visible_text_and_title() -> None:
  html = b"""<!doctype html>
  <html><head><title>Privacy Policy</title></head>
  <body>
    <h1>Privacy Policy</h1>
    <p>We collect account data.</p>
  </body></html>
  """
  result = HtmlParser().parse(html)

  assert result.title == "Privacy Policy"
  assert "# Privacy Policy" in result.raw_text
  assert "We collect account data." in result.raw_text
  assert "<p>" not in result.raw_text


def test_html_parser_drops_script_and_style() -> None:
  html = (
    b"<html><body>"
    b"<style>h1 { color: red; }</style>"
    b"<script>alert('x')</script>"
    b"<p>Visible clause.</p>"
    b"</body></html>"
  )
  result = HtmlParser().parse(html)

  assert "Visible clause." in result.raw_text
  assert "alert" not in result.raw_text
  assert "color: red" not in result.raw_text


def test_html_parser_unescapes_entities() -> None:
  html = b"<p>Terms &amp; conditions apply.</p>"
  result = HtmlParser().parse(html)

  assert "Terms & conditions apply." in result.raw_text


def test_html_parser_rejects_undecodable_bytes() -> None:
  with pytest.raises(UnreadableDocumentError, match="Failed to decode"):
    HtmlParser().parse(b"\xff\xfe\x00\x00", encoding="utf-8")


def test_loader_loads_html_and_htm(tmp_path: Path, document_loader: DocumentLoader) -> None:
  html = "<html><body><h2>Your rights</h2><p>You may request deletion.</p></body></html>"
  html_path = tmp_path / "policy.html"
  htm_path = tmp_path / "policy.htm"
  html_path.write_text(html, encoding="utf-8")
  htm_path.write_text(html, encoding="utf-8")

  loaded_html = document_loader.process(_source(html_path))
  loaded_htm = document_loader.process(_source(htm_path))

  assert loaded_html.metadata.format == DocumentFormat.HTML
  assert loaded_htm.metadata.format == DocumentFormat.HTML
  assert "## Your rights" in loaded_html.raw_text
  assert "You may request deletion." in loaded_htm.raw_text
