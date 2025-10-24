#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/ops/runtime_state.json"
MODE=$(jq -r '.mode' "$STATE" 2>/dev/null || echo "full")
PAR=$(jq -r '.max_parallel_jobs' "$STATE" 2>/dev/null || echo "2")

echo "[guarded] mode=$MODE parallel=$PAR  ts=$(date -Is)"

# 1) 自愈与限制（restricted/abstain/baseline 时降低速率）
case "$MODE" in
  restricted)  THROTTLE=800 ;;   # 毫秒
  abstain)     THROTTLE=1600 ;;
  baseline)    THROTTLE=0 ;;     # 由策略回退控制
  *)           THROTTLE=0 ;;
esac
export WHALE_THROTTLE_MS="${THROTTLE}"

# 2) 按并发值串行/并行调用（与原脚本兼容）
#    这里只示意：根据 PAR 重复调用原来的小时流水线（串行退让）。
for i in $(seq 1 "$PAR"); do
  ( [[ "$THROTTLE" -gt 0 ]] && sleep 0.$((RANDOM%5)); \
    "$ROOT/scripts/hourly_pipeline.sh" ) &
done
wait
echo "[guarded] done"

# ==== F-stage tail marker ====
# 可选观测：一致性评分 + 基线对比（失败不影响主流程）
if [ -x "$(dirname "$0")/f_stage_tail.sh" ]; then
  "$(dirname "$0")/f_stage_tail.sh" >>"$(cd "$(dirname "$0")/.." && pwd)/logs/cron_hourly.log" 2>&1 || true
fi
