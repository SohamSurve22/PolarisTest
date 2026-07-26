"""Stable document identifier generation."""

from __future__ import annotations

import uuid


def generate_document_id() -> str:
  """Return a stable internal document identifier (e.g. ``DOC_8f2c91d4``)."""
  return f"DOC_{uuid.uuid4().hex[:8]}"
