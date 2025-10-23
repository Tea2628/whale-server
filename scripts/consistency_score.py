#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F-Stage | Consistency Scorer (MVP)
输入：registry 索引、evidence 产物、audit 事件、metrics 指标、budget_state
输出：
  - dashboards/consistency.json  （含各分项与总分）
  - dashboards/metrics.json      （追加 consistency_score_overall）
  - audit.event=consistency_score
权重（F清单）：
  contract_validity 30、evidence_coverage 20、kpi_non_regression 20、
  drift_check 10、risk_budget_integrity 10、reproducibility 10
"""
import json, os, time, pathlib

AUDIT="audit/audit.jsonl"
METRICS="dashboards/metrics.json"
OUT="dashboards/consistency.json"
REG_LATEST="evidence/schema_registry/LATEST_INDEX.json"
BUDGET="evidence/budget_state.json"

pathlib.Path("dashboards").mkdir(parents=True, exist_ok=True)
pathlib.Path("audit").mkdir(parents=True, exist_ok=True)

def load(p, d=None):
    try:
        with open(p) as f: return json.load(f)
    except Exception:
        return d

def tail_events(name_set, last_n=800):
    res={k:0 for k in name_set}
    try:
        with open(AUDIT,'rb') as f:
            data=f.read().decode(errors='ignore').splitlines()[-last_n:]
        for ln in data:
            try:
                j=json.loads(ln)
                ev=j.get("event")
                if ev in res: res[ev]+=1
            except: pass
    except: pass
    return res

def most_recent_ok(event_name, key="ok", last_n=800):
    try:
        with open(AUDIT,'rb') as f:
            data=f.read().decode(errors='ignore').splitlines()[-last_n:]
        for ln in reversed(data):
            try:
                j=json.loads(ln)
                if j.get("event")==event_name:
                    meta=j.get("meta",{})
                    val = meta.get(key, True)
                    return bool(val)
            except: pass
    except: pass
    return False

# 1) contract_validity：有 LATEST_INDEX.json 且包含 entries>0 记满分；否则按覆盖比给分
latest = load(REG_LATEST, {"entries":[]})
entries = latest.get("entries", [])
contract_validity = 100.0 if len(entries)>0 else 0.0

# 2) evidence_coverage：三件套存在性粗略评估
e_required = [
    "evidence/bucket_kpi",
    "evidence/dataset_manifest",
    "evidence/ope_report"
]
covered = sum(1 for d in e_required if os.path.exists(d) and any(True for _ in os.scandir(d)))  # 非空目录算覆盖
evidence_coverage_ratio = covered/len(e_required)
evidence_coverage = round(evidence_coverage_ratio*100, 2)

# 3) kpi_non_regression：最近 audit 中没有 quality_gate_enforce 的 rollback 判定视为 100，否则扣到 60
#   （MVP 粗略：只看是否出现过该事件）
ev = tail_events({"quality_gate_enforce"})
kpi_non_regression = 60.0 if ev.get("quality_gate_enforce",0)>0 else 100.0

# 4) drift_check：最近存在 drift_alert 则 60，否则 100
ev2 = tail_events({"drift_alert"})
drift_check = 60.0 if ev2.get("drift_alert",0)>0 else 100.0

# 5) risk_budget_integrity：budget_used <= budget_total 则 100，否则 0
bs = load(BUDGET, {"budget_total":1.0,"budget_used":0.0})
risk_budget_integrity = 100.0 if bs.get("budget_used",0.0) <= bs.get("budget_total",1.0) else 0.0

# 6) reproducibility：最近一次 replay_consistency ok=True 则 100，否则 50
reproducibility = 100.0 if most_recent_ok("replay_consistency","ok") else 50.0

# 汇总（权重）
score = (
    contract_validity * 0.30 +
    evidence_coverage * 0.20 +
    kpi_non_regression * 0.20 +
    drift_check * 0.10 +
    risk_budget_integrity * 0.10 +
    reproducibility * 0.10
)
score = round(score, 2)

# 写 dashboards/consistency.json
out = {
  "ts": int(time.time()),
  "weights": {
    "contract_validity": 30, "evidence_coverage": 20, "kpi_non_regression": 20,
    "drift_check": 10, "risk_budget_integrity": 10, "reproducibility": 10
  },
  "components": {
    "contract_validity": contract_validity,
    "evidence_coverage": evidence_coverage,
    "kpi_non_regression": kpi_non_regression,
    "drift_check": drift_check,
    "risk_budget_integrity": risk_budget_integrity,
    "reproducibility": reproducibility
  },
  "evidence": {
    "registry_entries": len(entries),
    "evidence_coverage_ratio": evidence_coverage_ratio
  },
  "score": score
}
with open(OUT,"w") as f: json.dump(out,f,ensure_ascii=False,indent=2)

# 更新 metrics（只追加/覆盖本键）
metrics = load(METRICS, {})
metrics["consistency_score_overall"] = score
with open(METRICS,"w") as f: json.dump(metrics,f,ensure_ascii=False,indent=2)

# 写审计
audit_rec = {
  "ts": out["ts"], "event": "consistency_score", "actor": "system",
  "ref": "F-stage-MVP", "meta": {"score": score, **out["components"], **out["evidence"]}
}
with open(AUDIT,"a") as f: f.write(json.dumps(audit_rec, ensure_ascii=False)+"\n")

print(f"[consistency] score={score}  components=" +
      f"cv={contract_validity}, ec={evidence_coverage}, kpi={kpi_non_regression}, drift={drift_check}, rbi={risk_budget_integrity}, repro={reproducibility}")
