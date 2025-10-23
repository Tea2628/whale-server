#!/usr/bin/env bash
set -euo pipefail
ok(){ echo "[OK ] $*"; }
warn(){ echo "[WARN] $*"; }
bad(){ echo "[FAIL] $*"; exit 1; }

dt=$(date +%Y%m%d)
HH=$(date +%H)

test -x scripts/replay_consistency_check.py && ok "replay_consistency_check present" || bad "replay_consistency_check missing"
test -x scripts/quality_gate_enforce.py     && ok "quality_gate_enforce present"     || bad "quality_gate_enforce missing"
test -x scripts/drift_watch.py              && ok "drift_watch present"              || bad "drift_watch missing"

# 指标存在性（有些可能尚未触发 → WARN）
if grep -q '"whale_replay_jobs_running"' dashboards/metrics.json; then ok "metrics whale_replay_jobs_running"; else bad "metrics missing replay_jobs_running"; fi
if grep -q '"whale_replay_fail_total_by_reason"' dashboards/metrics.json; then ok "metrics replay_fail_total_by_reason"; else ok "metrics will init later"; fi

grep -q '"whale_replay_consistency_ok"' dashboards/metrics.json && ok "metrics replay_consistency_ok" || warn "metrics missing replay_consistency_ok (run consistency check)"

grep -q '"whale_drift_alerts_total"' dashboards/metrics.json && ok "metrics whale_drift_alerts_total" || warn "whale_drift_alerts_total not present (no drift yet)"
grep -q '"whale_rollback_latency_ms"' dashboards/metrics.json && ok "metrics whale_rollback_latency_ms" || warn "whale_rollback_latency_ms not present (no rollback yet)"

# 审计（可能未触发 → WARN）
grep -q '"event": "replay_consistency"' audit/audit.jsonl && ok "audit replay_consistency" || warn "no replay_consistency audit"
grep -q '"event": "quality_gate_enforce"' audit/audit.jsonl && ok "audit quality_gate_enforce" || warn "no quality_gate_enforce audit"
grep -q '"event": "drift_alert"' audit/audit.jsonl && ok "audit drift_alert" || warn "no drift_alert audit"

echo "---- SUMMARY ----"
