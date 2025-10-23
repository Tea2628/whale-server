#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
. "$ROOT/.venv/bin/activate"
python3 "$ROOT/scripts/gate_lite.py" < "$1"
