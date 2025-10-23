#!/usr/bin/env bash
set -euo pipefail

PASS=0; FAIL=0
ok(){ echo "[OK ] $1"; PASS=$((PASS+1)); }
bad(){ echo "[FAIL] $1"; FAIL=$((FAIL+1)); }

TODAY=$(date +%Y%m%d)

# 1) 关键脚本存在
test -f scripts/gate_policy_wrapper.py && ok "scripts/gate_policy_wrapper.py present" || bad "gate_policy_wrapper.py missing"
test -f scripts/policy_reload_probe.py && ok "scripts/policy_reload_probe.py present" || bad "policy_reload_probe.py missing"
test -f scripts/bucket_kpi_rollup.py && ok "scripts/bucket_kpi_rollup.py present" || bad "bucket_kpi_rollup.py missing"

# 2) gate 策略文件与阈值
if [ -f policies/gate_policy.yaml ]; then
  grep -qE 'conf_accept:\s*0\.6' policies/gate_policy.yaml && ok "gate_policy.yaml conf_accept=0.6" || bad "gate_policy.yaml conf_accept not 0.6"
  grep -qE 'conf_abstain:\s*0\.0' policies/gate_policy.yaml && ok "gate_policy.yaml conf_abstain=0.0" || bad "gate_policy.yaml conf_abstain not 0.0"
else
  bad "policies/gate_policy.yaml missing"
fi

# 3) dashboards 指标：reload latency + bucket_kpi_summary
if [ -f dashboards/metrics.json ]; then
  grep -q '"whale_policy_reload_latency_ms"' dashboards/metrics.json && ok "metrics has whale_policy_reload_latency_ms" || bad "metrics missing whale_policy_reload_latency_ms"
  grep -q '"bucket_kpi_summary"' dashboards/metrics.json && ok "metrics has bucket_kpi_summary" || bad "metrics missing bucket_kpi_summary"
else
  bad "dashboards/metrics.json missing"
fi

# 4) evidence 存在当日 rollup
if [ -f "evidence/bucket_kpi/${TODAY}_rollup.json" ]; then
  ok "evidence bucket_kpi rollup exists (${TODAY})"
else
  bad "evidence bucket_kpi rollup missing (${TODAY})"
fi

# 5) 审计事件齐全（任意时间范围的尾部检索）
AUD="audit/audit.jsonl"
if [ -f "$AUD" ]; then
  tail -n 500 "$AUD" | grep -q '"event": "template_apply"' && ok "audit has template_apply" || bad "audit missing template_apply"
  tail -n 500 "$AUD" | grep -q '"event": "registry_update"' && ok "audit has registry_update" || bad "audit missing registry_update"
  tail -n 500 "$AUD" | grep -q '"event": "experiment_phase"' && ok "audit has experiment_phase" || bad "audit missing experiment_phase"
  tail -n 500 "$AUD" | grep -q '"event": "bucket_kpi_rollup"' && ok "audit has bucket_kpi_rollup" || bad "audit missing bucket_kpi_rollup"
else
  bad "audit/audit.jsonl missing"
fi

echo "---- SUMMARY ----"
echo "pass=$PASS fail=$FAIL"
test "$FAIL" -eq 0
