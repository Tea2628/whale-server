#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "[F-tail] start ts=$(date -Is)"
# 一致性评分（Spec/Config/Runtime/Audit → metrics + audit）
/home/tm/repos/whale-server/.venv/bin/python scripts/consistency_score.py || echo "[F-tail] consistency_score failed"
# 基线对比（GOLDEN vs 当前快照 → metrics + audit）
/home/tm/repos/whale-server/.venv/bin/python scripts/baseline_guard.py --mode compare || echo "[F-tail] baseline_compare failed"
echo "[F-tail] done ts=$(date -Is)"
