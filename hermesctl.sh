#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_BIN="${HERMES_PYTHON:-python3}"

exec "$PYTHON_BIN" "$ROOT/hermesctl.py" "$@"
