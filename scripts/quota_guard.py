#!/usr/bin/env python3
import sys, json, time, hashlib, pathlib
AUDIT="audit/audit.jsonl"; STATE="evidence/quota_state.json"
DEFAULT_QUOTA=200
def load_state():
    try: return json.load(open(STATE))
    except: return {"ts":0,"by_tenant":{}}
def save_state(s):
    pathlib.Path("evidence").mkdir(parents=True, exist_ok=True)
    json.dump(s, open(STATE,"w"), ensure_ascii=False, indent=2)
def audit(meta):
    rec={"ts":int(time.time()),"event":"quota_guard","actor":"system",
         "ref":hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:16],
         "meta":meta}
    pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
    open(AUDIT,"a").write(json.dumps(rec,ensure_ascii=False)+"\n")

raw=sys.stdin.read().strip()
msg=json.loads(raw) if raw else {}
tenant=msg.get("tenant_id","t_demo"); day=time.strftime("%Y%m%d", time.gmtime())
st=load_state(); t=st["by_tenant"].setdefault(tenant, {})
rec=t.setdefault(day, {"used":0,"quota":DEFAULT_QUOTA})
decision="allow"
if rec["used"] >= rec["quota"]:
    decision="throttle"
else:
    rec["used"]+=1
st["ts"]=int(time.time()); save_state(st)
audit({"tenant":tenant,"day":day,"used":rec["used"],"quota":rec["quota"],"decision":decision})
if decision=="throttle":
    print(json.dumps({"decision":"delay","reason":"quota_exceeded","tenant":tenant},ensure_ascii=False)); sys.exit(0)
print(json.dumps(msg,ensure_ascii=False))
