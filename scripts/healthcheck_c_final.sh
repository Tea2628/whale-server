#!/usr/bin/env bash
set -euo pipefail

ok(){ echo "[OK ] $*"; }
bad(){ echo "[FAIL] $*"; exit 1; }

dt=$(date +%Y%m%d)
HH=$(date +%H)

# 可执行脚本存在性
test -x scripts/ledger_demo_emit.py        && ok "ledger_demo_emit present"        || bad "ledger_demo_emit missing"
test -x scripts/manifest_make.py           && ok "manifest_make present"           || bad "manifest_make missing"
test -x scripts/ledger_sha_roll.py         && ok "ledger_sha_roll present"         || bad "ledger_sha_roll missing"
test -x scripts/ledger_retention.py        && ok "ledger_retention present"        || bad "ledger_retention missing"
test -x scripts/delayed_reward_validate.py && ok "delayed_reward_validate present" || bad "delayed_reward_validate missing"
test -x scripts/replay_harness_min.py      && ok "replay_harness_min present"      || bad "replay_harness_min missing"

# manifest 中是否包含延迟收益分区
grep -q "delayed_reward_ledger/dt=${dt}" manifest/dt=${dt}/manifest.json \
  && ok "manifest includes delayed_reward_ledger" \
  || bad "manifest missing delayed_reward_ledger"

# 今日小时分区的 SHA256SUMS / RECORDS
for d in \
  ledger/market_tick/dt=${dt}/symbol=BTCUSDT \
  ledger/features/dt=${dt}/symbol=BTCUSDT \
  ledger/signals/dt=${dt}/symbol=BTCUSDT \
  ledger/gate/dt=${dt}/symbol=BTCUSDT \
  ledger/delayed_reward_ledger/dt=${dt}/symbol=BTCUSDT \
  ledger/policy_change/dt=${dt}
do
  test -d "$d" || continue
  if test -f "$d/SHA256SUMS" && test -f "$d/RECORDS"; then
    ok "SHA/RECORDS ok: $d"
  else
    bad "SHA/RECORDS missing: $d"
  fi
done

# 证据文件
test -s evidence/ope_report/${dt}_ope_report.json \
  && ok "OPE evidence ok" \
  || bad "OPE evidence missing"

test -s evidence/quality_card/${dt}_quality_card.json \
  && ok "QualityCard evidence ok" \
  || bad "QualityCard evidence missing"

# 仪表盘关键字段
grep -q '"quality_gate_verdict"' dashboards/metrics.json \
  && ok "metrics has quality_gate_verdict" \
  || bad "metrics missing quality_gate_verdict"

grep -q '"quality_gate_tuned"' dashboards/metrics.json \
  && ok "metrics has quality_gate_tuned" \
  || bad "metrics missing quality_gate_tuned"

# 审计事件
grep -q '"event": "manifest_make"'           audit/audit.jsonl && ok "audit manifest_make"            || bad "audit missing manifest_make"
grep -q '"event": "ledger_sha_roll"'         audit/audit.jsonl && ok "audit ledger_sha_roll"          || bad "audit missing ledger_sha_roll"
grep -q '"event": "ledger_retention"'        audit/audit.jsonl && ok "audit ledger_retention"         || bad "audit missing ledger_retention"
grep -q '"event": "delayed_reward_validate"' audit/audit.jsonl && ok "audit delayed_reward_validate"  || bad "audit missing delayed_reward_validate"
grep -q '"event": "ope_report_make"'         audit/audit.jsonl && ok "audit ope_report_make"          || bad "audit missing ope_report_make"
grep -q '"event": "quality_card_make"'       audit/audit.jsonl && ok "audit quality_card_make"        || bad "audit missing quality_card_make"

echo "---- SUMMARY ----"
