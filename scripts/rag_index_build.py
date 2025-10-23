#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, time, hashlib, pathlib
KB_DIR="knowledge"
EVID_DIR="evidence"
AUDIT="audit/audit.jsonl"
METRICS="dashboards/metrics.json"
IDX=f"{EVID_DIR}/knowledge_index.jsonl"
LATEST=f"{EVID_DIR}/KNOWLEDGE_LATEST.json"

pathlib.Path(EVID_DIR).mkdir(parents=True, exist_ok=True)
pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
pathlib.Path("dashboards").mkdir(parents=True, exist_ok=True)

def sha256sum(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def load(p,d={}):
    try: return json.load(open(p))
    except: return d

ts=int(time.time())
entries=[]
for fn in sorted(os.listdir(KB_DIR)) if os.path.isdir(KB_DIR) else []:
    p=os.path.join(KB_DIR,fn)
    if not os.path.isfile(p): continue
    with open(p,'r',encoding='utf-8', errors='ignore') as f:
        text=f.read()
    title = (text.splitlines()[0] if text else fn).strip("# ").strip() or fn
    entries.append({
        "ts": ts, "name": title, "path": p,
        "sha256": sha256sum(p), "bytes": os.path.getsize(p)
    })

with open(IDX,"a") as out:
    for e in entries: out.write(json.dumps(e,ensure_ascii=False)+"\n")

json.dump({"ts":ts,"entries":entries}, open(LATEST,"w"), ensure_ascii=False, indent=2)

m=load(METRICS,{})
m["rag_docs_total"]=len(entries)
m["rag_last_build_ts"]=ts
json.dump(m, open(METRICS,"w"), ensure_ascii=False, indent=2)

open(AUDIT,"a").write(json.dumps({
    "ts":ts,"event":"rag_index_build","actor":"system","ref":"F-stage",
    "meta":{"docs":len(entries)}
}, ensure_ascii=False)+"\n")

print(f"[rag] indexed docs={len(entries)} -> {IDX}")
