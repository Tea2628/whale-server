#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
. "$ROOT/.venv/bin/activate"
DIR="$ROOT/signals/$(date +%Y%m%d)"
shopt -s nullglob
for f in "$DIR"/*.json; do
  python3 "$ROOT/scripts/deliver.py" "$f"
done
