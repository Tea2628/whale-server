#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, time, sys, pathlib, subprocess

METRICS = "dashboards/metrics.json"
CONSISTENCY = "dashboards/consistency.json"
REG_LATEST = "evidence/schema_registry/LATEST_INDEX.json"
GATE_OUT_DIR = "evidence/gate_report"

def jload(p, d=None):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d

def run(cmd):
    try:
        return subprocess.run(cmd, shell=True, check=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        return e

def contract_gate():
    # 用“期望意识”校验器代表 Schema Registry 全量通过
    r = run("python3 tools/validate_contracts_expected.py")
    ok = (isinstance(r, subprocess.CompletedProcess) and r.returncode == 0)
    return ("pass" if ok else "reject", r.stdout.strip() if r else "no out")

def consistency_gate(metrics, cons):
    score = int(metrics.get("consistency_score_overall", 0) or 0)
    ok = score >= 85 and bool(cons)
    reason = f"score={score}"
    return ("pass" if ok else "reject", reason)

def redlines_gate():
    # 判定口径：1) citation 至少通过过 1 次；2) 最近一次 forbidden_gate 的 meta.ok == True
    m = jload(METRICS, {})
    cit_ok = m.get("rag_citation_pass_total", 0) >= 1

    last_ok = False
    try:
        import json
        last = None
        with open("audit/audit.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("event") == "forbidden_gate":
                    last = rec
        if last and isinstance(last.get("meta"), dict):
            last_ok = bool(last["meta"].get("ok", False))
    except Exception:
        last_ok = False

    ok = cit_ok and last_ok
    reason = f"citation_pass_total={m.get('rag_citation_pass_total',0)}, last_forbidden_ok={last_ok}"
    return ("pass" if ok else "reject", reason)


def main():
    version = None
    channel = "beta"
    for i,a in enumerate(sys.argv):
        if a == "--version" and i+1<len(sys.argv): version = sys.argv[i+1]
        if a == "--channel" and i+1<len(sys.argv): channel = sys.argv[i+1]
    if not version:
        version = "v0.4.0-beta"

    metrics = jload(METRICS, {})
    cons = jload(CONSISTENCY, {})
    gates = {}
    reasons = []

    g, r = contract_gate();   gates["contract"]=g;    reasons.append(f"contract:{'ok' if g=='pass' else 'fail'} {r.splitlines()[-1:]}")
    g, r = consistency_gate(metrics, cons); gates["consistency"]=g; reasons.append(f"consistency:{r}")
    g, r = redlines_gate();   gates["redlines"]=g;    reasons.append(f"redlines:{r}")

    decision = "pass" if all(v=="pass" for v in gates.values()) else "reject"

    rec = {
        "ts": int(time.time()),
        "version": version,
        "channel": channel,
        "decision": decision,
        "gates": gates,
        "reasons": reasons,
        "metrics": {k:metrics.get(k) for k in [
            "consistency_score_overall","rag_citation_pass_total","redline_block_total",
            "whale_auto_rollback_total","whale_drift_alerts_total"
        ] if k in metrics},
        "artifacts": {
            "registry_index": REG_LATEST if os.path.exists(REG_LATEST) else "",
            "consistency_json": CONSISTENCY if os.path.exists(CONSISTENCY) else "",
            "metrics_json": METRICS
        }
    }

    pathlib.Path(GATE_OUT_DIR).mkdir(parents=True, exist_ok=True)
    outp = os.path.join(GATE_OUT_DIR, f"{time.strftime('%Y%m%d_%H%M%S')}_gate_report.json")
    with open(outp,"w") as f: json.dump(rec, f, ensure_ascii=False, indent=2)
    with open(os.path.join(GATE_OUT_DIR, "LATEST.json"),"w") as f: json.dump(rec, f, ensure_ascii=False, indent=2)

    # 写审计
    pathlib.Path("audit").mkdir(exist_ok=True)
    with open("audit/audit.jsonl","a") as f:
        f.write(json.dumps({"ts":rec["ts"],"event":"release_gate","actor":"system","ref":version,
                            "meta":{"decision":decision,"gates":gates}} ,ensure_ascii=False)+"\n")

    print(f"[gate] decision={decision} | gates={gates} -> {outp}")

if __name__ == "__main__":
    main()
