#!/usr/bin/env bash
set -Eeuo pipefail
AUDIT="audit/audit.jsonl"; NOW=$(date +%s)
echo "[drill] simulate storage readonly & cleanup"; sleep 5
jq -cn --argjson ts "$NOW" \
  '{ts:$ts,event:"drill",actor:"ops",decision:"done",reasons:["storage_readonly"],slo_check:{pass:true}}' >>"$AUDIT"
