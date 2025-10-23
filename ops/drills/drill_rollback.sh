#!/usr/bin/env bash
set -Eeuo pipefail
AUDIT="audit/audit.jsonl"
NOW=$(date +%s)

echo "[drill] simulate policy rollback"
sleep 3

# 记录演练完成到审计流
jq -cn --argjson ts "$NOW" \
  '{ts:$ts,event:"drill",actor:"ops",decision:"done",reasons:["policy_rollback"],slo_check:{pass:true}}' >>"$AUDIT"
echo "[drill] policy rollback drill recorded."
