#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forbidden_gate.py
stdin: {"text":"..."} 或 {"answer":"..."} 或 {"lines":["...","..."]}
stdout: {"pass":true/false,"matches":[...]}
副作用：写 audit(event=forbidden_gate)；更新 metrics: redline_block_total / redline_pass_total
"""
import sys, json, time, pathlib, re, hashlib

AUDIT="audit/audit.jsonl"
METRICS="dashboards/metrics.json"
RULES="policies/forbidden_patterns.txt"

pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
pathlib.Path("dashboards").mkdir(parents=True, exist_ok=True)

def load_metrics():
    try:
        import json
        with open(METRICS) as f: return json.load(f)
    except: return {}
def save_metrics(m):
    with open(METRICS,"w") as f: json.dump(m,f,ensure_ascii=False,indent=2)

def load_rules():
    pats=[]
    try:
        with open(RULES,encoding="utf-8") as f:
            for ln in f:
                ln=ln.strip()
                if not ln or ln.startswith("#"): continue
                pats.append(re.compile(ln))
    except Exception:
        pass
    return pats

def write_audit(meta):
    rec={"ts":int(time.time()),"event":"forbidden_gate","actor":"system",
         "ref":hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:16],
         "meta":meta}
    with open(AUDIT,"a") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")

raw=sys.stdin.read().strip()
try:
    data=json.loads(raw) if raw else {}
except Exception:
    print(json.dumps({"pass":False,"matches":["parse_error"]},ensure_ascii=False)); sys.exit(0)

text=""
if isinstance(data.get("lines"),list):
    text="\n".join(map(str,data["lines"]))
else:
    text=str(data.get("text") or data.get("answer") or "")

patterns=load_rules()
matches=[]
for pat in patterns:
    try:
        m=pat.search(text)
        if m:
            snippet=m.group(0)
            matches.append(snippet[:64])
    except Exception:
        pass

ok = (len(matches)==0)
write_audit({"ok":ok,"hits":len(matches),"samples":matches[:3]})
m=load_metrics()
key = "redline_pass_total" if ok else "redline_block_total"
m[key] = int(m.get(key,0)) + 1
save_metrics(m)

print(json.dumps({"pass":ok,"matches":matches},ensure_ascii=False))
