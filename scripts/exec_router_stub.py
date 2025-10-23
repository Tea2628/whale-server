#!/usr/bin/env python3
# Minimal exec router stub: reads one JSON line (order_request-like), writes audit
import sys, json, time, hashlib, pathlib
AUDIT="audit/audit.jsonl"
pathlib.Path("audit").mkdir(parents=True, exist_ok=True)

raw = sys.stdin.read().strip()
try:
    req = json.loads(raw)
    req_id = str(req.get("request_id",""))
    signal_id = str(req.get("signal_id",""))
    # 写入审计事件
    rec = {
        "ts": int(time.time()),
        "event": "exec_router_stub",
        "actor": "system",
        "ref": hashlib.sha256(raw.encode()).hexdigest()[:16],
        "meta": {"request_id": req_id, "signal_id": signal_id, "status": "accepted"}
    }
    with open(AUDIT,"a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")
    print("[exec-router] accepted:", req_id or "(no-id)")
except Exception as e:
    rec = {
        "ts": int(time.time()),
        "event": "exec_router_stub",
        "actor": "system",
        "ref": "parse_error",
        "meta": {"error": str(e)}
    }
    with open(AUDIT,"a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")
    print("[exec-router] parse_error:", e, file=sys.stderr)
    sys.exit(1)
