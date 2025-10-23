#!/usr/bin/env bash
set -Eeuo pipefail
REQ=("evidence/bucket_kpi" "dashboards/metrics.json" "runbooks/D-Stage.md")
FREEZE_FILE="ops/freeze_window.on"
AUDIT="audit/audit.jsonl"

# 冻结窗：一律拒绝（如需只允许自愈，设置 OPS_SELF_HEAL=1 则放行）
if [[ -f "$FREEZE_FILE" && "${OPS_SELF_HEAL:-0}" != "1" ]]; then
  echo "[ops-gate] 🧊 freeze window active, only self-healing allowed."
  jq -cn --argjson ts "$(date +%s)" \
     '{ts:$ts,event:"ops_change",actor:"system",decision:"reject",reasons:["freeze_window"],slo_check:{pass:false}}' >>"$AUDIT"
  exit 1
fi

missing=()
for p in "${REQ[@]}"; do [[ -e "$p" ]] || missing+=("$p"); done
if (( ${#missing[@]} )); then
  jq -cn --argjson ts "$(date +%s)" --arg miss "${missing[*]}" \
     '{ts:$ts,event:"ops_change",actor:"system",decision:"reject",reasons:($miss|split(" ")),slo_check:{pass:false}}' >>"$AUDIT"
  echo "[ops-gate] ❌ reject (missing): ${missing[*]}" >&2
  exit 1
fi

jq -cn --argjson ts "$(date +%s)" \
   '{ts:$ts,event:"ops_change",actor:"system",decision:"allow",reasons:["preflight_ok"],slo_check:{pass:true}}' >>"$AUDIT"
echo "[ops-gate] ✅ allow"
