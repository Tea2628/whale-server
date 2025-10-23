#!/usr/bin/env python3
import sys, json, time, hashlib, pathlib
AUDIT="audit/audit.jsonl"; OUT="evidence/billing_events.jsonl"
def audit(meta):
    rec={"ts":int(time.time()),"event":"billing_event","actor":"system",
         "ref":hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:16],
         "meta":meta}
    pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
    open(AUDIT,"a").write(json.dumps(rec,ensure_ascii=False)+"\n")
pathlib.Path("evidence").mkdir(parents=True, exist_ok=True)
raw=sys.stdin.read().strip()
msg=json.loads(raw) if raw else {}
tenant=msg.get("tenant_id","t_demo")
evt={"tenant_id":tenant,"ts":int(time.time()),"event_type":"usage",
     "amount": 1.0, "currency":"USDT","ref": msg.get("request_id","sig_usage")}
open(OUT,"a").write(json.dumps(evt,ensure_ascii=False)+"\n")
audit(evt)
print(json.dumps(msg,ensure_ascii=False))
