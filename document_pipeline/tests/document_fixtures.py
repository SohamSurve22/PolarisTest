"""Helpers for creating sample documents in tests."""

from pathlib import Path

from docx import Document as DocxDocument
from reportlab.pdfgen import canvas


def write_txt(path: Path, content: str, *, encoding: str = "utf-8") -> Path:
  path.write_text(content, encoding=encoding)
  return path


def write_pdf(
  path: Path,
  text: str,
  *,
  title: str | None = None,
  author: str | None = None,
) -> Path:
  pdf = canvas.Canvas(str(path))
  if title is not None:
    pdf.setTitle(title)
  if author is not None:
    pdf.setAuthor(author)
  pdf.drawString(72, 720, text)
  pdf.save()
  return path


def write_docx(
  path: Path,
  paragraphs: list[str],
  *,
  title: str | None = None,
  author: str | None = None,
) -> Path:
  document = DocxDocument()
  properties = document.core_properties
  if title is not None:
    properties.title = title
  if author is not None:
    properties.author = author

  for paragraph in paragraphs:
    document.add_paragraph(paragraph)

  document.save(path)
  return path
