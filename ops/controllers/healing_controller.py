#!/usr/bin/env python3
import json, time, hashlib, pathlib

METRICS = "dashboards/metrics.json"
STATE   = "ops/runtime_state.json"
AUDIT   = "audit/audit.jsonl"

def audit(meta):
    rec = {
        "ts": int(time.time()),
        "event": "healing",
        "actor": "system",
        "ref": hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest()[:16],
        "decision": meta.get("decision", "observe"),
        "reasons": meta.get("reasons", []),
        "slo_check": meta.get("slo_check", {"pass": True})
    }
    with open(AUDIT, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def load_json(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default

m = load_json(METRICS, {})
slo_bad = False
reasons = []

# 依据 D 阶段口径（简化判断门槛）
if m.get("healing_mTTR_ms_rolling1h", 0) > 60000:
    slo_bad = True; reasons.append("healing_mTTR>60s")
if m.get("retention_gap_files_total", 0) > 0:
    slo_bad = True; reasons.append("retention_gap>0")
if m.get("secrets_rotation_age_days", 0) > 90:
    slo_bad = True; reasons.append("secrets_rotation_expired")

state = load_json(STATE, {"mode": "full", "max_parallel_jobs": 2, "last_change_ts": 0})
new_mode = "restricted" if slo_bad else "full"

changed = state.get("mode") != new_mode
state["mode"] = new_mode
if changed:
    state["last_change_ts"] = int(time.time())
pathlib.Path(STATE).write_text(json.dumps(state, indent=2, ensure_ascii=False))

audit({"decision": new_mode if changed else "noop", "reasons": reasons, "slo_check": {"pass": not slo_bad}})
