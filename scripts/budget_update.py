#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stdin: 一条 risk_guard_decision 或 execution_report（JSON）
stdout: 一条 budget_state（JSON）
规则（MVP）：
- 对 risk_guard_decision:
    allow/resize -> 依据 final_qty(若有) 或原 qty(需通过上游传入 meta.qty) 记入临时“占用” budget_used += qty*risk_budget_factor
    reject/delay -> 不占用，仅审计
- 对 execution_report:
    filled/partially_filled -> budget_used += filled_qty * fill_factor（简单处理）
    canceled/rejected/expired -> 不变
"""
import sys, json, time, pathlib, hashlib

AUDIT="audit/audit.jsonl"
STATE="evidence/budget_state.json"  # 简单状态文件，非账本；账本由 pnl_ledger 覆盖
TENANT="t_demo"
KLASS="A"

def write_audit(event, meta):
    rec={"ts":int(time.time()),"event":event,"actor":"system",
         "ref":hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:16],
         "meta":meta}
    pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
    with open(AUDIT,"a") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")

def load_state():
    try:
        with open(STATE) as f: return json.load(f)
    except Exception:
        return {"ts":0,"tenant_id":TENANT,"klass":KLASS,"budget_total":1.0,"budget_used":0.0,"cooldown_s":0}

def save_state(s):
    pathlib.Path("evidence").mkdir(parents=True, exist_ok=True)
    with open(STATE,"w") as f: json.dump(s,f,ensure_ascii=False,indent=2)

raw=sys.stdin.read().strip()
if not raw:
    print("{}", end=""); sys.exit(0)

state=load_state()
now=int(time.time())

try:
    msg=json.loads(raw)
except Exception as e:
    write_audit("budget_update", {"error":f"parse_error:{e}"})
    print(json.dumps(state,ensure_ascii=False)); sys.exit(1)

# 处理两类输入
updated=False
if "decision" in msg and "request_id" in msg:
    # risk_guard_decision
    decision=msg.get("decision")
    final_qty=msg.get("final_qty")
    meta_qty=msg.get("meta_qty")  # 可由上游传递原始 qty
    qty = final_qty if isinstance(final_qty,(int,float)) and final_qty is not None else (meta_qty or 0.0)
    factor=0.01  # 演示：每单位占用 1% 预算
    if decision in ("allow","resize") and qty>0:
        state["budget_used"]=round(state.get("budget_used",0.0) + qty*factor, 8)
        updated=True
    write_audit("budget_update", {"source":"risk_guard","decision":decision,"qty":qty,"new_budget_used":state["budget_used"]})

elif "status" in msg and "request_id" in msg:
    # execution_report
    status=msg.get("status")
    filled=msg.get("filled_qty") or 0.0
    fill_factor=0.005  # 演示：成交按 0.5% 占用
    if status in ("filled","partially_filled") and filled>0:
        state["budget_used"]=round(state.get("budget_used",0.0) + filled*fill_factor, 8)
        updated=True
    write_audit("budget_update", {"source":"execution","status":status,"filled_qty":filled,"new_budget_used":state["budget_used"]})

# 规范化输出
state["ts"]=now
state["tenant_id"]=state.get("tenant_id",TENANT)
state["klass"]=state.get("klass",KLASS)

save_state(state)
print(json.dumps(state,ensure_ascii=False))
