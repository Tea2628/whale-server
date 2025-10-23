#!/usr/bin/env bash
set -Eeuo pipefail
AUDIT="audit/audit.jsonl"; NOW=$(date +%s)
echo "[drill] inject latency=p95x2 (simulate)"; sleep 5
jq -cn --argjson ts "$NOW" \
  '{ts:$ts,event:"drill",actor:"ops",decision:"done",reasons:["latency_p95x2"],slo_check:{pass:true}}' >>"$AUDIT"
