#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABCED Self-Check (read-only):
- A: contracts/samples, gate-lite, deliver, audit, dead_letter
- B: KPI rollup, policy reload, gate policy, bucket_kpi evidence
- C: ledgers, manifest, replay, quality card, OPE, dataset_manifest
- D: controllers (healing/capacity), ops gate (freeze), retention, drills, runtime_state, cron venv
- E: execution/SaaS contracts + stubs + audit chain
Exit code: 0 if all PASS, 1 otherwise
"""
import os, json, time, re, sys, glob, pathlib

ROOT="."
NOW=time.time()
DAY=86400

def ok(x): return f"✅ {x}"
def bad(x): return f"❌ {x}"
def exists(p): return os.path.exists(p)
def recent(p, within=DAY*3): # 3d window
    try: return NOW - os.path.getmtime(p) <= within
    except: return False
def read_json(p, default=None):
    try:
        with open(p) as f: return json.load(f)
    except: return default

def any_glob(patterns):
    for pat in patterns:
        if glob.glob(pat): return True
    return False

report=[]; failed=False
def check(cond, title, hint=""):
    global failed
    if cond:
        report.append(ok(title))
    else:
        failed=True
        report.append(bad(f"{title}" + (f"  → {hint}" if hint else "")))

# ---------------- A ----------------
check(exists("schemas/json/signal.schema.json"), "A|schema: signal")
check(exists("schemas/json/gateway_attempt.schema.json"), "A|schema: gateway_attempt")
check(any_glob(["samples/signal/valid/*.json"]), "A|samples: signal valid")
check(exists("scripts/gate_lite.py"), "A|gate-lite script")
check(exists("scripts/deliver.py"), "A|deliver script")
check(exists("audit/audit.jsonl") and recent("audit/audit.jsonl", within=DAY*7), "A|audit stream recent", "audit/audit.jsonl too old?")
check(any_glob(["release/*/*"]), "A|release artifacts present")
check(exists("dead_letter/dead_sig_bad01.json"), "A|dead_letter exists")

# ---------------- B ----------------
check(exists("scripts/gate_policy_wrapper.py"), "B|policy wrapper")
check(exists("scripts/policy_reload_probe.py"), "B|policy reload probe")
check(exists("policies/gate_policy.yaml"), "B|gate policy")
check(any_glob(["evidence/bucket_kpi/*_kpi.jsonl","evidence/bucket_kpi/*rollup*.json"]), "B|bucket_kpi evidence")
check(exists("dashboards/metrics.json"), "B|metrics.json")

# ---------------- C ----------------
check(any_glob(["ledger/*/dt=*"]), "C|ledgers present")
check(exists("manifest/dt=20251023/manifest.json") or any_glob(["manifest/dt=*/manifest.json"]), "C|manifest daily")
check(exists("manifest/dataset_manifest.jsonl"), "C|dataset_manifest.jsonl")
check(exists("evidence/dataset_manifest/20251023_dataset_manifest.json") or any_glob(["evidence/dataset_manifest/*_dataset_manifest.json"]), "C|dataset_manifest (evidence)")
check(exists("evidence/replay_job/20251023_replay_job.json") or any_glob(["evidence/replay_job/*.json"]), "C|replay_job evidence")
check(exists("evidence/quality_card/20251023_quality_card.json") or any_glob(["evidence/quality_card/*.json"]), "C|quality_card evidence")
check(exists("evidence/ope_report/20251023_ope_report.json") or any_glob(["evidence/ope_report/*.json"]), "C|OPE report")

# ---------------- D ----------------
check(exists("ops/controllers/healing_controller.py"), "D|healing controller")
check(exists("ops/controllers/capacity_controller.py"), "D|capacity controller")
check(exists("ops/gate/ops_gate_preflight.sh"), "D|ops gate preflight")
check(exists("ops/retention/retention_rotate.py"), "D|retention rotate")
check(any_glob(["ops/drills/drill_*.sh"]), "D|drills present")
check(exists("ops/runtime_state.json"), "D|runtime_state.json")
# cron venv: try to read crontab dump if user exported; fallback to logs as proof
cron_ok = any(" .venv/bin/python " in line for line in os.popen("crontab -l 2>/dev/null"))
check(cron_ok or any_glob(["logs/healing.log","logs/capacity.log"]), "D|cron uses venv (or logs present)", "ensure crontab uses .venv/bin/python")

# ---------------- E ----------------
# schemas
for name in ["order_request","risk_guard_decision","execution_report",
             "budget_state","position_state","pnl_ledger",
             "tenant","quota_policy","billing_event","strategy_pool"]:
    check(exists(f"schemas/json/{name}.schema.json"), f"E|schema: {name}")

# stubs
check(exists("scripts/policy_router_stub.py"), "E|stub: policy_router")
check(exists("scripts/risk_guard_pre.py"), "E|stub: risk_guard_pre")
check(exists("scripts/budget_update.py"), "E|stub: budget_update")
check(exists("scripts/auth_stub.py"), "E|stub: auth_stub")
check(exists("scripts/quota_guard.py"), "E|stub: quota_guard")
check(exists("scripts/billing_logger.py"), "E|stub: billing_logger")
check(exists("scripts/exec_router_stub.py"), "E|stub: exec_router_stub")

# audit chain presence (tail scan)
audit_tail = []
try:
    with open("audit/audit.jsonl","r") as f:
        audit_tail = [line.strip() for line in f.readlines()[-200:]]
except: pass

def audit_has(ev): return any(f'"event": "{ev}"' in ln for ln in audit_tail)
for ev in ["order_flow","risk_guard","budget_update","billing_event","exec_router_stub"]:
    check(audit_has(ev), f"E|audit event: {ev}", "run the e2e demo if missing")

# summary banner
print("\n=== ABCDE SELF-CHECK SUMMARY ===")
for line in report: print(line)

# exit code
sys.exit(0 if not failed else 1)
