#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, json, time, pathlib, hashlib, glob, random

AUDIT = "audit/audit.jsonl"
STRATEGY_SAMPLES = ["samples/strategy_pool/valid/*.json", "samples/strategy_pool/edge/*.json"]

def load_strategies():
    files = []
    for pat in STRATEGY_SAMPLES:
        files.extend(glob.glob(pat))
    strategies = []
    for p in files:
        try:
            with open(p) as f:
                s = json.load(f)
                strategies.append(s)
        except Exception:
            pass
    # 先选 status=active，其次 canary，否则随机取一个
    active = [s for s in strategies if s.get("status") == "active"]
    canary = [s for s in strategies if s.get("status") == "canary"]
    if active:
        return random.choice(active)
    if canary:
        return random.choice(canary)
    return random.choice(strategies) if strategies else {
        "strategy_id":"sp_default","name":"Default","version":"1.0.0","klass":"C","status":"active",
        "params":{"symbols":["BTCUSDT"],"cooldown_s":60}
    }

def write_audit(event, meta):
    rec = {"ts": int(time.time()), "event": event, "actor": "system",
           "ref": hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest()[:16],
           "meta": meta}
    pathlib.Path("audit").mkdir(parents=True, exist_ok=True)
    with open(AUDIT, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")

raw = sys.stdin.read().strip()
signal = {}
try:
    signal = json.loads(raw) if raw else {}
except Exception:
    print("[router] invalid signal json", file=sys.stderr); sys.exit(1)

symbol = str(signal.get("symbol","BTCUSDT"))
confidence = float(signal.get("confidence", 0.6))
side = signal.get("side", "buy" if confidence >= 0 else "sell")
qty = float(signal.get("qty", 0.01))

strategy = load_strategies()
req_id = f"req_{int(time.time())}"
order = {
  "request_id": req_id,
  "signal_id": signal.get("signal_id","sig_demo"),
  "symbol": symbol,
  "side": side,
  "qty": qty,
  "order_type": "market",
  "limit_price": None,
  "ttl_s": 30,
  "slippage_bps_max": 20,
  "client_order_id": f"coid_{int(time.time()*1000)}",
  "risk_budget": 0.05 if strategy.get("klass") == "A" else 0.02,
  "policy_ref": strategy.get("strategy_id","sp_default"),
  "tenant_id": signal.get("tenant_id","t_demo")
}

write_audit("order_flow", {
  "strategy_id": strategy.get("strategy_id"),
  "status": strategy.get("status"),
  "klass": strategy.get("klass"),
  "symbol": symbol,
  "side": side,
  "confidence": confidence,
  "order_request_id": req_id
})

# 输出一条 order_request JSON 到 stdout，便于后续接 exec_router_stub
print(json.dumps(order, ensure_ascii=False))
