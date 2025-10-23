#!/usr/bin/env bash
set -euo pipefail
ok(){ echo "[OK ] $*"; }
bad(){ echo "[FAIL] $*"; }

dt=$(date +%Y%m%d); HH=$(date +%H)

test -x scripts/ledger_append.py && ok "ledger_append.py present" || bad "ledger_append.py missing"
test -x scripts/ledger_demo_emit.py && ok "ledger_demo_emit.py present" || bad "ledger_demo_emit.py missing"
test -x scripts/manifest_make.py && ok "manifest_make.py present" || bad "manifest_make.py missing"

# 目录结构
test -d ledger/market_tick && ok "ledger/market_tick exists" || bad "ledger/market_tick missing"
test -d manifest && ok "manifest exists" || bad "manifest missing"

# 今日分区是否有文件
find ledger -type f -name "$HH.jsonl" | grep -q "dt=$dt" && ok "today hourly files exist" || bad "no hourly files for today"

# manifest 是否生成
test -s manifest/dt=$dt/manifest.json && ok "manifest today's file exists" || bad "manifest missing for today"

# audit 是否记录 manifest 事件
grep -q '"event": "manifest_make"' audit/audit.jsonl && ok "audit has manifest_make" || bad "audit miss manifest_make"

echo "---- SUMMARY ----"
