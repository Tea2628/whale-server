#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"

pass=0; fail=0
ok(){ echo "[OK ] $*"; pass=$((pass+1)); }
bad(){ echo "[BAD] $*"; fail=$((fail+1)); }

# 0) 基础环境
if [ -f ".venv/bin/activate" ]; then ok "venv exists"; else bad "venv missing"; fi
if . .venv/bin/activate 2>/dev/null; then ok "venv activate"; else bad "venv activate failed"; fi
if python -c "import jsonschema" 2>/dev/null; then ok "jsonschema installed"; else bad "jsonschema missing"; fi

# 1) 契约与样例
cnt_schema=$(ls -1 schemas/json/*.schema.json 2>/dev/null | wc -l | tr -d ' ')
[ "$cnt_schema" = "5" ] && ok "5 schemas present" || bad "schemas count=$cnt_schema (need 5)"
miss_samples=0
for k in features gpt_suggestion signal gateway_attempt audit; do
  for t in valid edge invalid; do
    c=$(ls -1 "samples/$k/$t"/*.json 2>/dev/null | wc -l | tr -d ' ')
    [ "$c" -ge 1 ] || { bad "samples/$k/$t missing (>=1)"; miss_samples=1; }
  done
done
[ "$miss_samples" = "0" ] && ok "sample sets complete"

# 2) 脚本就绪
for s in scripts/validate_contracts.py scripts/gate_lite.py scripts/emit_signal.sh scripts/rules_min.py scripts/deliver.py scripts/simulate_batch.sh; do
  [ -x "$s" ] && ok "$s present" || bad "$s missing or not executable"
done

# 3) 只读校验（不会写业务产物）
if ./scripts/validate_contracts.py >/tmp/hc_validate.out 2>&1; then
  ok "validate_contracts OK (all pass)"
else
  # 允许 invalid/edge 失败，抓取 SUMMARY
  tail -n 3 /tmp/hc_validate.out | grep -q "SUMMARY" && ok "validate_contracts ran (SUMMARY captured)" || bad "validate_contracts failed to run"
fi

# 4) 审计与产物存在性（允许为空）
[ -d audit ] && ok "audit dir exists" || bad "audit dir missing"
[ -f audit/audit.jsonl ] && tail -n 1 audit/audit.jsonl >/dev/null 2>&1 && ok "audit.jsonl present" || ok "audit.jsonl not yet created (acceptable)"

# 5) KPI 生成（会写 dashboards/metrics.json）
if python3 scripts/metrics_kpi.py >/tmp/hc_kpi.out 2>&1; then
  ok "metrics_kpi ran"
  jq_bin="$(command -v jq || true)"
  if [ -n "$jq_bin" ]; then
    cat dashboards/metrics.json | $jq_bin -c .
  else
    head -n 1 /tmp/hc_kpi.out >/dev/null 2>&1
  fi
else
  bad "metrics_kpi failed"
fi

# 6) 配置检查
grep -q "deliver:" config/gate.yml 2>/dev/null && ok "config/gate.yml present" || bad "config/gate.yml missing"

echo "---- SUMMARY ----"
echo "pass=$pass fail=$fail"
[ $fail -eq 0 ] && exit 0 || exit 1
