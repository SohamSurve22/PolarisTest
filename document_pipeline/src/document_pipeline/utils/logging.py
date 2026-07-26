"""Centralized logging configuration for the document pipeline."""

import logging
import sys
from functools import lru_cache

from document_pipeline.config.settings import get_settings


def configure_logging(level: str | None = None) -> None:
  """Configure the root logger with pipeline-wide settings.

  Args:
    level: Optional log level override. Defaults to settings value.
  """
  settings = get_settings()
  log_level = level or settings.log_level

  logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format=settings.log_format,
    handlers=[logging.StreamHandler(sys.stderr)],
    force=True,
  )


@lru_cache
def get_logger(name: str) -> logging.Logger:
  """Return a named logger, configuring logging on first use."""
  if not logging.getLogger().handlers:
    configure_logging()
  return logging.getLogger(name)
