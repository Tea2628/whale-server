#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stdin: 一条 JSON：
{
  "answer": "字符串回答",
  "citations": [{"path":"knowledge/policies.md","quote":"...原文片段..."}, ...]
}
输出：{"pass": true/false, "failed": [...]} 并写审计 event=citation_gate
指标：rag_citation_pass_total / rag_citation_fail_total 计数
"""
import sys, json, time, pathlib, hashlib

AUDIT="audit/audit.jsonl"
METRICS="dashboards/metrics.json"
pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
pathlib.Path("dashboards").mkdir(parents=True, exist_ok=True)

def load_json(p,d):
    try:
        import json
        with open(p) as f: return json.load(f)
    except: return d

def save_json(p,o):
    with open(p,"w") as f: json.dump(o,f,ensure_ascii=False,indent=2)

raw=sys.stdin.read().strip()
try:
    payload=json.loads(raw)
except Exception as e:
    print(json.dumps({"pass":False,"failed":["parse_error"]},ensure_ascii=False)); sys.exit(0)

citations=payload.get("citations") or []
failed=[]

for c in citations:
    path=c.get("path"); quote=c.get("quote","")
    try:
        with open(path,'r',encoding='utf-8',errors='ignore') as f:
            txt=f.read()
        if (quote or "").strip() and (quote in txt):
            continue
        else:
            failed.append(f"mismatch:{path}")
    except Exception:
        failed.append(f"not_found:{path}")

ok = (len(citations)>0 and len(failed)==0)

# 审计
meta={"ok":ok,"failed":failed,"citations":citations}
rec={"ts":int(time.time()),"event":"citation_gate","actor":"system",
     "ref":hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:16],
     "meta":meta}
open(AUDIT,"a").write(json.dumps(rec,ensure_ascii=False)+"\n")

# 指标
m=load_json(METRICS,{})
key = "rag_citation_pass_total" if ok else "rag_citation_fail_total"
m[key] = int(m.get(key,0)) + 1
save_json(METRICS,m)

print(json.dumps({"pass":ok,"failed":failed},ensure_ascii=False))
