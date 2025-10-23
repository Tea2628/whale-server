#!/usr/bin/env bash
set -euo pipefail
ok(){ echo "[OK ] $*"; }
bad(){ echo "[FAIL] $*"; }

dt=$(date +%Y%m%d)

# 文件存在性
test -s evidence/ope_report/${dt}_ope_report.json && ok "OPE evidence exists" || bad "missing OPE evidence"
test -s evidence/quality_card/${dt}_quality_card.json && ok "QualityCard evidence exists" || bad "missing QualityCard evidence"

# 仪表盘字段
if grep -q '"quality_gate_verdict"' dashboards/metrics.json; then
  ok "metrics has quality_gate_verdict"
  echo -n "verdict: "
  grep -o '"quality_gate_verdict":[^}]*}' dashboards/metrics.json | head -n1
else
  bad "metrics missing quality_gate_verdict"
fi

# 审计事件
grep -q '"event": "ope_report_make"' audit/audit.jsonl && ok "audit has ope_report_make" || bad "audit missing ope_report_make"
grep -q '"event": "quality_card_make"' audit/audit.jsonl && ok "audit has quality_card_make" || bad "audit missing quality_card_make"

echo "---- SUMMARY ----"
