#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F-Stage | Baseline Guard (snapshot + compare + make-golden)
用途：
  - snapshot：生成当前快照（SNAPSHOT_YYYYMMDD_HHMMSS.json）
  - make-golden：以当前快照写入 GOLDEN.json（建立黄金基线）
  - compare：把当前快照与 GOLDEN.json 对比，写审计与指标
产物：
  evidence/baseline/SNAPSHOT_*.json
  evidence/baseline/GOLDEN.json
副作用：
  dashboards/metrics.json 追加 baseline_drift_files_total / baseline_ok
  audit/audit.jsonl 追加 baseline_snapshot / baseline_drift 事件
"""
import os, sys, json, time, hashlib, pathlib, argparse

AUDIT="audit/audit.jsonl"
METRICS="dashboards/metrics.json"
BASE_DIR="evidence/baseline"
INCLUDE = [
  "schemas/json",
  "policies",
  "ops/controllers",
  "ops/gate",
  "scripts/gate_policy_wrapper.py",
  "scripts/policy_reload_probe.py",
  "scripts/metrics_kpi.py",
  "scripts/manifest_make.py",
  "scripts/replay_harness_min.py",
  "scripts/consistency_score.py",
  "scripts/forbidden_gate.py",
  "scripts/citation_gate.py",
  "scripts/rag_index_build.py"
]
EXCLUDE_SUFFIX = {".pyc", ".log"}
EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "logs", "release", "ledger"}

pathlib.Path(BASE_DIR).mkdir(parents=True, exist_ok=True)
pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
pathlib.Path("dashboards").mkdir(parents=True, exist_ok=True)

def sha256sum(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def iter_files(root):
    if os.path.isfile(root):
        yield root; return
    if not os.path.isdir(root): return
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d not in EXCLUDE_DIRS]
        for fn in fs:
            if any(fn.endswith(suf) for suf in EXCLUDE_SUFFIX): continue
            yield os.path.join(r, fn)

def build_snapshot():
    files=[]
    for p in INCLUDE:
        for f in iter_files(p):
            try:
                files.append({"path":f, "sha256":sha256sum(f), "size":os.path.getsize(f)})
            except Exception:
                pass
    snap={"ts":int(time.time()), "files":sorted(files, key=lambda x:x["path"])}
    return snap

def write_audit(event, meta):
    rec={"ts":int(time.time()),"event":event,"actor":"system",
         "ref":hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:16],
         "meta":meta}
    with open(AUDIT,"a") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")

def load_json(p, d=None):
    try:
        with open(p) as f: return json.load(f)
    except Exception:
        return d

def save_metrics(upd):
    m=load_json(METRICS,{})
    m.update(upd)
    with open(METRICS,"w") as f: json.dump(m,f,ensure_ascii=False,indent=2)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["snapshot","compare","make-golden"], required=True)
    args=ap.parse_args()

    if args.mode=="snapshot":
        snap=build_snapshot()
        out=os.path.join(BASE_DIR, time.strftime("SNAPSHOT_%Y%m%d_%H%M%S.json", time.gmtime(snap["ts"])))
        json.dump(snap, open(out,"w"), ensure_ascii=False, indent=2)
        write_audit("baseline_snapshot", {"path":out, "files":len(snap["files"])})
        print(f"[baseline] snapshot -> {out} files={len(snap['files'])}")
        return

    if args.mode=="make-golden":
        snap=build_snapshot()
        golden=os.path.join(BASE_DIR, "GOLDEN.json")
        json.dump(snap, open(golden,"w"), ensure_ascii=False, indent=2)
        write_audit("baseline_snapshot", {"path":golden, "files":len(snap["files"]), "golden":True})
        print(f"[baseline] GOLDEN updated -> {golden} files={len(snap['files'])}")
        return

    if args.mode=="compare":
        snap=build_snapshot()
        golden_path=os.path.join(BASE_DIR, "GOLDEN.json")
        golden=load_json(golden_path, {"files":[]})
        gmap={f["path"]:f["sha256"] for f in golden.get("files",[])}
        drift=[]
        for f in snap["files"]:
            gsha=gmap.get(f["path"])
            if gsha is None:
                drift.append({"path":f["path"],"type":"added"})
            elif gsha != f["sha256"]:
                drift.append({"path":f["path"],"type":"modified"})
        # 检查删除
        smap={f["path"] for f in snap["files"]}
        for p in gmap.keys():
            if p not in smap:
                drift.append({"path":p,"type":"deleted"})

        drift_total=len(drift)
        save_metrics({"baseline_drift_files_total": drift_total, "baseline_ok": (1 if drift_total==0 else 0)})
        write_audit("baseline_drift", {"golden":os.path.exists(golden_path), "drift_total": drift_total, "drift":drift[:10]})
        out=os.path.join(BASE_DIR, time.strftime("SNAPSHOT_%Y%m%d_%H%M%S.json", time.gmtime(snap["ts"])))
        json.dump(snap, open(out,"w"), ensure_ascii=False, indent=2)
        print(f"[baseline] compare -> drift_total={drift_total} (snapshot={out})")
        if drift_total>0:
            for d in drift[:10]:
                print(" -", d["type"], d["path"])
        return

if __name__=="__main__":
    main()
