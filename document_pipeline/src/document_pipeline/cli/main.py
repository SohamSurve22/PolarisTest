"""CLI entry point — delegates to pipeline services without business logic."""

from __future__ import annotations

import argparse
import sys

from document_pipeline.cli.preview import register_preview_command
from document_pipeline.config.settings import get_settings
from document_pipeline.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
  """Build the argument parser for the CLI."""
  settings = get_settings()
  parser = argparse.ArgumentParser(
    prog="document-pipeline",
    description=settings.app_name,
  )
  parser.add_argument(
    "--log-level",
    default=None,
    help="Override the configured log level (e.g. DEBUG, INFO).",
  )
  parser.add_argument(
    "--version",
    action="version",
    version="%(prog)s 0.1.0",
  )

  subparsers = parser.add_subparsers(dest="command")
  register_preview_command(subparsers)

  return parser


def main(argv: list[str] | None = None) -> int:
  """CLI main entry point.

  Args:
    argv: Optional argument list for testing.

  Returns:
    Process exit code.
  """
  parser = build_parser()
  args = parser.parse_args(argv)

  configure_logging(level=args.log_level)

  if args.command is None:
    parser.print_help()
    return 0

  handler = getattr(args, "handler", None)
  if handler is None:
    parser.print_help()
    return 0

  logger.info("Running CLI command: %s", args.command)
  return int(handler(args))


if __name__ == "__main__":
  sys.exit(main())
