"""Command-line entry point for the vectorization package."""

from __future__ import annotations

import logging

from vectorization.config import get_settings
from vectorization.pipeline import run


def main() -> None:
  settings = get_settings()
  logging.basicConfig(level=settings.log_level)
  run(settings)


if __name__ == "__main__":
  main()
