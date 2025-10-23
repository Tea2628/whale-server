#!/usr/bin/env bash
set -Eeuo pipefail
AUDIT="audit/audit.jsonl"; NOW=$(date +%s)
what="${1:-telegram_token}"
jq -cn --argjson ts "$NOW" --arg w "$what" \
  '{ts:$ts,event:"secrets",actor:"ops",decision:"rotate",reasons:[$w],slo_check:{pass:true}}' >>"$AUDIT"
echo "[secrets] rotate stub for $what recorded."
