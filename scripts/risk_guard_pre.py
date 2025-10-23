#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
risk_guard_pre.py
stdin:  一条 order_request JSON
stdout: 一条 risk_guard_decision JSON
规则（最小演示）：
- qty > 0.02 -> resize 到 0.02
- risk_budget > 0.08 -> reject
- 非白名单 symbol -> delay（白名单: BTCUSDT, ETHUSDT, SOLUSDT）
- 其他 -> allow
并写 audit:event="risk_guard"
"""
import sys, json, time, hashlib, pathlib

AUDIT="audit/audit.jsonl"
ALLOWED={"BTCUSDT","ETHUSDT","SOLUSDT"}

def write_audit(meta):
    rec={"ts":int(time.time()),"event":"risk_guard","actor":"system",
         "ref":hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:16],
         "meta":meta}
    pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
    with open(AUDIT,"a") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")

raw=sys.stdin.read().strip()
try:
    req=json.loads(raw)
except Exception as e:
    print(json.dumps({"request_id":None,"decision":"reject","reasons":[f"parse_error:{e}"],"final_qty":None,"guards":{}}))
    write_audit({"request_id":None,"decision":"reject","reasons":[f"parse_error:{e}"]})
    sys.exit(1)

req_id=req.get("request_id","")
symbol=str(req.get("symbol","BTCUSDT"))
qty=float(req.get("qty",0.0) or 0.0)
risk_budget=float(req.get("risk_budget",0.0) or 0.0)

decision="allow"; reasons=[]; final_qty=None

if risk_budget>0.08:
    decision="reject"; reasons.append("risk_budget_exceeds_limit")
elif symbol not in ALLOWED:
    decision="delay"; reasons.append("symbol_not_whitelisted")
elif qty>0.02:
    decision="resize"; final_qty=0.02; reasons.append("resize_max_qty=0.02")

out={"request_id":req_id,"decision":decision,"reasons":reasons,"final_qty":final_qty,"guards":{"precheck":True}}
print(json.dumps(out,ensure_ascii=False))

write_audit({"request_id":req_id,"symbol":symbol,"qty":qty,"risk_budget":risk_budget,"decision":decision,"final_qty":final_qty,"reasons":reasons})
