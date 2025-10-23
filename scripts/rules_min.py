#!/usr/bin/env python3
import json, sys, time, uuid, pathlib

def clamp(x,a,b): return max(a, min(b, x))

def gen_signal(feat: dict) -> dict:
    # 基于最小启发：micro_price > mid_price → buy，否则 sell
    side = "buy" if feat.get("micro_price",0) >= feat.get("mid_price",0) else "sell"
    # 置信度：从 spread_bps 反向映射到 [0.55, 0.75]
    spread = float(feat.get("spread_bps", 1.0))
    conf = clamp(0.75 - spread/100.0, 0.55, 0.75)
    level = "A" if conf >= 0.60 else ("B" if conf >= 0.55 else "C")
    sig = {
        "id": f"sim_{uuid.uuid4().hex[:8]}",
        "ts": int(feat.get("ts", time.time()*1000)),
        "symbol": feat.get("symbol","BTCUSDT"),
        "side": side,
        "level": level,
        "conf": round(conf, 3),
        "expected_pnl": 10.0,           # 占位：A阶段仿真
        "risk_budget": 0.05,            # 占位：A阶段仿真
        "ttl_s": 60,
        "abstain": False,
        "reasons": [f"spread_bps={spread}", f"micro_vs_mid={feat.get('micro_price',0)}>{feat.get('mid_price',0)}"],
        "policy_ref": "sg_sim_min_v1",
        "contract_version": "1.0.0"
    }
    return sig

def main():
    if len(sys.argv) < 2:
        print("usage: rules_min.py <features.json>", file=sys.stderr)
        sys.exit(2)
    feat = json.load(open(sys.argv[1]))
    sig = gen_signal(feat)
    json.dump(sig, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()
