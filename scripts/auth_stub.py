#!/usr/bin/env python3
import sys, json, time, hashlib, pathlib
AUDIT="audit/audit.jsonl"; ALLOW={"t_demo"}
def audit(meta):
    rec={"ts":int(time.time()),"event":"auth_check","actor":"system",
         "ref":hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:16],
         "meta":meta}
    pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
    open(AUDIT,"a").write(json.dumps(rec,ensure_ascii=False)+"\n")
raw=sys.stdin.read().strip()
msg=json.loads(raw) if raw else {}
tenant=msg.get("tenant_id","t_demo")
ok=tenant in ALLOW
audit({"tenant":tenant,"ok":ok})
if not ok:
    print(json.dumps({"error":"unauthorized","tenant":tenant},ensure_ascii=False)); sys.exit(1)
print(json.dumps(msg,ensure_ascii=False))
