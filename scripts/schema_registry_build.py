#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, time, hashlib, json, pathlib, re, sys

SCHEMAS_DIR = "schemas/json"
SAMPLES_DIR = "samples"
EVID_DIR = "evidence/schema_registry"
AUDIT = "audit/audit.jsonl"
METRICS = "dashboards/metrics.json"

pathlib.Path(EVID_DIR).mkdir(parents=True, exist_ok=True)
pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
pathlib.Path("dashboards").mkdir(parents=True, exist_ok=True)

def sha256sum(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def load_json(p, default):
    try:
        with open(p) as f: return json.load(f)
    except Exception:
        return default

def write_audit(event, meta):
    rec = {"ts": int(time.time()), "event": event, "actor": "system", "ref": meta.get("ref",""), "meta": meta}
    with open(AUDIT, "a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")

# 1) 收集 schema
schemas = []
for fn in sorted(os.listdir(SCHEMAS_DIR)) if os.path.isdir(SCHEMAS_DIR) else []:
    if not fn.endswith(".schema.json"): continue
    p = os.path.join(SCHEMAS_DIR, fn)
    name = fn.replace(".schema.json","")
    ver = "v1"
    try:
        data = load_json(p, {})
        # 简单地把 $id 或 title 当作 version/名称线索
        title = data.get("title") or name
        if isinstance(title,str): name = title
    except Exception:
        pass
    schemas.append({"name": name, "path": p, "sha256": sha256sum(p), "version": ver, "samples": []})

# 2) 收集样例并映射到 schema（按目录名推断）
samples_map = {}  # schema_name -> [paths]
if os.path.isdir(SAMPLES_DIR):
    for root, _, files in os.walk(SAMPLES_DIR):
        for fn in files:
            if not fn.endswith(".json"): continue
            p = os.path.join(root, fn)
            # 取 samples/<folder>/.../<file>.json 中的 <folder> 作为 schema name 尝试归类
            parts = pathlib.Path(p).parts
            try:
                idx = parts.index("samples")
                cat = parts[idx+1]
            except Exception:
                cat = "unknown"
            samples_map.setdefault(cat, []).append(p)

# 3) 将样例挂接到对应 schema
for s in schemas:
    cat = s["name"] if s["name"] in samples_map else s["name"].replace("_","")
    # 容错：严格匹配失败则尝试用文件名（去掉 .schema）
    alt = s["path"].split("/")[-1].replace(".schema.json","")
    s["samples"] = sorted(set(samples_map.get(s["name"], []) + samples_map.get(alt, []) + samples_map.get(cat, [])))

# 4) 输出当日注册清单（append-only）与最新索引
ts = int(time.time())
reg_jl = os.path.join(EVID_DIR, time.strftime("%Y%m%d_", time.gmtime(ts)) + "REGISTRY.jsonl")
total = 0
with open(reg_jl, "a") as out:
    for s in schemas:
        entry = {"ts": ts, "kind": "schema", "name": s["name"], "path": s["path"], "sha256": s["sha256"], "version": s["version"], "samples": s["samples"]}
        out.write(json.dumps(entry, ensure_ascii=False) + "\n"); total += 1
        for sp in s["samples"]:
            out.write(json.dumps({"ts": ts, "kind":"sample","name": s["name"], "path": sp, "sha256": sha256sum(sp), "version": s["version"], "samples": []}, ensure_ascii=False) + "\n"); total += 1

# 5) 写最新索引快照
latest_idx = os.path.join(EVID_DIR, "LATEST_INDEX.json")
index = {"ts": ts, "entries": [{"name": s["name"], "path": s["path"], "sha256": s["sha256"], "samples": s["samples"]} for s in schemas]}
with open(latest_idx, "w") as f: json.dump(index, f, ensure_ascii=False, indent=2)

# 6) 更新 metrics：覆盖率与一致性（粗略）
covered = sum(1 for s in schemas if s["samples"])
coverage = round(covered / max(len(schemas),1), 3)
metrics = load_json(METRICS, {})
metrics.update({"scl_schema_total": len(schemas), "scl_coverage_ratio": coverage, "scl_last_build_ts": ts})
with open(METRICS, "w") as f: json.dump(metrics, f, ensure_ascii=False, indent=2)

# 7) 审计
write_audit("schema_registry_build", {"ref": os.path.basename(reg_jl), "schemas": len(schemas), "coverage": coverage})
print(f"[scl] registry -> {reg_jl} | schemas={len(schemas)} coverage={coverage}")
