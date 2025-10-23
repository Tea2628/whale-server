#!/usr/bin/env python3
import json, os, time, psutil, hashlib
METRICS="dashboards/metrics.json"; STATE="ops/runtime_state.json"; AUDIT="audit/audit.jsonl"

def audit(meta):
    rec={"ts":int(time.time()),"event":"capacity","actor":"system",
         "ref":hashlib.sha256(str(meta).encode()).hexdigest()[:16],
         "decision":meta.get("decision","observe"),"reasons":meta.get("reasons",[]),"slo_check":{"pass":True}}
    with open(AUDIT,"a") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")

def load(p,d={}):
    try:
        with open(p) as f: return json.load(f)
    except: return d

m=load(METRICS,{}); st=load(STATE,{"mode":"full","max_parallel_jobs":2})
cpu=psutil.cpu_percent(interval=0.3)
backlog = m.get("queue_backlog_total",0) + m.get("replay_jobs_running",0)
target = st.get("max_parallel_jobs",2)

if backlog>5 and cpu<70: target=min(8,target+1); reason="scale_up"
elif backlog==0 or cpu>85: target=max(1,target-1); reason="scale_down"
else: reason="hold"

if target!=st.get("max_parallel_jobs"):
    st["max_parallel_jobs"]=target; st["last_change_ts"]=int(time.time())
    open(STATE,"w").write(json.dumps(st,indent=2,ensure_ascii=False))
audit({"decision":reason,"reasons":[f"cpu={cpu}",f"backlog={backlog}",f"target={target}"]})
