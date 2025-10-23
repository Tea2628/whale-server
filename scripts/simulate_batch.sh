#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"

CNT_ALL=0; CNT_ACC=0; CNT_ABS=0; CNT_REJ=0
for f in samples/features/valid/*.json; do
  [ -e "$f" ] || continue
  CNT_ALL=$((CNT_ALL+1))
  out="/tmp/sim_signal_$CNT_ALL.json"
  python3 scripts/rules_min.py "$f" > "$out"
  if ./scripts/emit_signal.sh "$out" | tee /dev/stderr | grep -q '^ACCEPT:'; then
    CNT_ACC=$((CNT_ACC+1))
  elif ./scripts/emit_signal.sh "$out" | tee /dev/stderr | grep -q '^ABSTAIN:'; then
    CNT_ABS=$((CNT_ABS+1))
  else
    CNT_REJ=$((CNT_REJ+1))
  fi
done

echo "BATCH_SUMMARY all=$CNT_ALL accept=$CNT_ACC abstain=$CNT_ABS reject=$CNT_REJ"
echo "signals_today=$(ls -1 signals/$(date +%Y%m%d) 2>/dev/null | wc -l)"
echo "dead_letters=$(ls -1 dead_letter 2>/dev/null | wc -l)"
tail -n 3 audit/audit.jsonl 2>/dev/null || true
