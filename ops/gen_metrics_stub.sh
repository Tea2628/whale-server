#!/usr/bin/env bash
set -Eeuo pipefail
f="dashboards/metrics.json"
jq -n \
  --arg ts "$(date +%s)" \
  '{ts:($ts|tonumber),
    service_uptime_ratio_7d: 0.999,
    healing_mTTR_ms_rolling1h: 1000,
    capacity_scale_events_total: 0,
    queue_backlog_total: 0,
    secrets_rotation_age_days: 10,
    retention_gap_files_total: 0,
    replay_jobs_running: 0
  }' > "$f"
echo "[metrics] stub refreshed -> $f"
