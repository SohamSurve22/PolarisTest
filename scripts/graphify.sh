#!/usr/bin/env bash
# Wrapper so agents can run graphify without a global install on PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/.venv/bin/graphify" "$@"
