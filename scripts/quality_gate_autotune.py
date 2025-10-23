#!/usr/bin/env python3
import json, time, pathlib, sys, subprocess
from typing import Tuple

try:
    import yaml
except Exception:
    print("FATAL: need PyYAML. Try: pip install pyyaml", file=sys.stderr); sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[1]
POL  = ROOT/"policies"/"gate_policy.yaml"
QC   = ROOT/"evidence"/"quality_card"
MET  = ROOT/"dashboards"/"metrics.json"
AUD  = ROOT/"audit"/"audit.jsonl"

RULE = {
  "pass":  ("decrease", 0.05, 0.55),  # 降低阈值，最低到 0.55
  "warn":  ("increase", 0.05, 0.75),  # 提高阈值，最多到 0.75
  "fail":  ("set",      0.90,  0.90), # 直接拉到 0.90
}

def today(): return time.strftime("%Y%m%d", time.localtime())

def load_yaml(p, default):
    try:
        return yaml.safe_load(open(p)) or default
    except Exception:
        return default

def load_json(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default

def save_yaml(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f: yaml.safe_dump(obj, f, sort_keys=False)

def save_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f: json.dump(obj, f, ensure_ascii=False, indent=2)

def tune(cur: float, verdict: str) -> float:
    kind, val, bound = RULE[verdict]
    if kind == "decrease":
        return max(bound, round(cur - val, 3))
    if kind == "increase":
        return min(bound, round(cur + val, 3))
    if kind == "set":
        return float(val)
    return cur

def main():
    dt = today()
    qc_path = QC/f"{dt}_quality_card.json"
    qc = load_json(qc_path, {})
    verdict = (qc.get("verdict") or "pass").lower()
    if verdict not in RULE:
        print(f"WARN: unknown verdict '{verdict}', skip."); sys.exit(0)

    pol = load_yaml(POL, {"policy":{"conf_accept":0.60, "conf_abstain":0.0}})
    cur = float(pol.get("policy",{}).get("conf_accept", 0.60))
    new = tune(cur, verdict)

    changed = (abs(new - cur) >= 1e-9)
    if changed:
        pol["policy"]["conf_accept"] = new
        pol["policy"]["conf_abstain"] = float(pol["policy"].get("conf_abstain", 0.0))
        save_yaml(POL, pol)

    # 更新仪表盘
    met = load_json(MET, {"date": dt})
    met["quality_gate_verdict"] = {"date": dt, "verdict": verdict}
    met["quality_gate_tuned"] = {
        "date": dt, "verdict": verdict,
        "conf_accept_before": cur, "conf_accept_after": new,
        "changed": bool(changed)
    }
    save_json(MET, met)

    # 写审计
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD, "a") as f:
        f.write(json.dumps({
            "event": "quality_gate_autotune",
            "ts": int(time.time()*1000),
            "actor": "service",
            "ref": dt,
            "meta": {"verdict": verdict, "before": cur, "after": new, "changed": changed},
            "explain": [f"policy conf_accept {cur} -> {new}" if changed else "no change"]
        }, ensure_ascii=False) + "\n")

    print(f"AUTOTUNE verdict={verdict} conf_accept {cur} -> {new} changed={changed}")
    sys.exit(0)

if __name__ == "__main__":
    main()
