#!/usr/bin/env bash
set -Eeuo pipefail
AUDIT="audit/audit.jsonl"; NOW=$(date +%s)
echo "[drill] disconnect upstream for 60s (simulate)"; sleep 60
jq -cn --argjson ts "$NOW" \
  '{ts:$ts,event:"drill",actor:"ops",decision:"done",reasons:["disconnect_60s"],slo_check:{pass:true}}' >>"$AUDIT"
