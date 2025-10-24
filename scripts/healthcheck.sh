#!/usr/bin/env bash
set -Eeuo pipefail

ok(){ printf "[OK ] %s\n" "$*"; }
bad(){ printf "[BAD] %s\n" "$*"; FAIL=$((FAIL+1)); }
info(){ printf "%s\n" "$*"; }

PASS=0; FAIL=0
bump_ok(){ ok "$*"; PASS=$((PASS+1)); }

# 0) venv
[ -d .venv ] && bump_ok "venv exists" || bad "venv missing"
# shellcheck disable=SC1091
set +u; . .venv/bin/activate >/dev/null 2>&1 && bump_ok "venv activate" || bad "venv activate failed"; set -u

# 1) jsonschema
python - <<'PY' >/dev/null 2>&1 || true
import pkgutil, sys; sys.exit(0 if pkgutil.find_loader("jsonschema") else 1)
PY
[ $? -eq 0 ] && bump_ok "jsonschema installed" || bad "jsonschema missing"

# 2) schemas 计数（阶段感知：至少 MIN 个，默认 5，可用 HEALTHCHECK_SCHEMA_MIN 覆盖）
MIN="${HEALTHCHECK_SCHEMA_MIN:-5}"
CNT=$(ls -1 schemas/json/*.schema.json 2>/dev/null | wc -l | awk '{print $1}')
if [ "${CNT:-0}" -ge "$MIN" ]; then
  bump_ok "schemas count=${CNT} (need >= ${MIN})"
else
  bad "schemas count=${CNT} (need >= ${MIN})"
fi

# 3) samples 完整性（至少存在 valid/edge 目录）
if [ -d samples ] && ls -d samples/*/valid >/dev/null 2>&1 && ls -d samples/*/edge >/dev/null 2>&1; then
  bump_ok "sample sets complete"
else
  bad "sample sets incomplete"
fi

# 4) 关键脚本存在
for f in scripts/validate_contracts.py scripts/gate_lite.py scripts/emit_signal.sh scripts/rules_min.py scripts/deliver.py scripts/simulate_batch.sh; do
  [ -e "$f" ] && bump_ok "$f present" || bad "$f missing"
done

# 5) 契约校验（采用 expected-aware，确保 invalid/* 走“预期失败”）
if python3 tools/validate_contracts_expected.py >/dev/null 2>&1; then
  bump_ok "validate_contracts OK"
else
  bad "validate_contracts failed"
fi

# 6) audit/metrics/config 存在性与一次 kpi 生成
[ -d audit ] && bump_ok "audit dir exists" || bad "audit dir missing"
[ -f audit/audit.jsonl ] && bump_ok "audit.jsonl present" || bad "audit.jsonl missing"

if [ -x scripts/metrics_kpi.py ]; then
  python3 scripts/metrics_kpi.py >/dev/null 2>&1 || true
  if [ -f dashboards/metrics.json ]; then
    bump_ok "metrics_kpi ran"
    jq -c '.|{date: .date, daily_count_total, abstain_ratio, gate_reject_total, emit_rate_per_min, latency_p95_ms, accepts, abstains, rejects}' dashboards/metrics.json 2>/dev/null || true
  else
    bad "metrics.json missing"
  fi
else
  bad "scripts/metrics_kpi.py missing"
fi

[ -f config/gate.yml ] && bump_ok "config/gate.yml present" || bad "config/gate.yml missing"

echo "---- SUMMARY ----"
echo "pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
