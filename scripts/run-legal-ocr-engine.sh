#!/bin/bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <input> [options]" >&2
  exit 2
fi

ROOT="$HOME/.workbuddy/legal-skills/ocr-router"
ENGINE="$ROOT/backends/legal-ocr-engine/scripts/convert.py"
PYTHON="$HOME/.workbuddy/binaries/python/envs/legal-ocr/bin/python"

if [ ! -f "$ENGINE" ]; then
  echo "ERROR: engine not found: $ENGINE" >&2
  exit 2
fi

if [ ! -x "$PYTHON" ]; then
  echo "ERROR: python not found: $PYTHON" >&2
  exit 2
fi

exec "$PYTHON" "$ENGINE" "$@"
