#!/usr/bin/env python3
import json, time, pathlib, subprocess, shlex, os

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP  = ROOT/"scripts"/"ledger_append.py"

def j(obj): return json.dumps(obj, ensure_ascii=False)

def run_append(path, obj):
    cmd = f"{shlex.quote(str(APP))} {shlex.quote(str(path))} {shlex.quote(j(obj))}"
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr.strip())
    print(out.stdout.strip())

def main():
    now = time.localtime()
    dt  = time.strftime("%Y%m%d", now)
    HH  = time.strftime("%H", now)
    sym = os.environ.get("SYM","BTCUSDT")

    # 5 个分区：market_tick / features / signals / gate / policy_change
    base = pathlib.Path("ledger")
    paths = {
        "market_tick":   base/"market_tick"/f"dt={dt}"/f"symbol={sym}"/f"{HH}.jsonl",
        "features":      base/"features"/f"dt={dt}"/f"symbol={sym}"/f"{HH}.jsonl",
        "signals":       base/"signals"/f"dt={dt}"/f"symbol={sym}"/f"{HH}.jsonl",
        "gate":          base/"gate"/f"dt={dt}"/f"symbol={sym}"/f"{HH}.jsonl",
        "policy_change": base/"policy_change"/f"dt={dt}"/f"{HH}.jsonl",
    }

    run_append(paths["market_tick"],   {"symbol": sym, "mid": 68000.5, "micro": 68001.1})
    run_append(paths["features"],      {"symbol": sym, "spread_bps": 0.7, "liq": "normal"})
    run_append(paths["signals"],       {"id": "demo_sig", "symbol": sym, "side": "buy", "conf": 0.74})
    run_append(paths["gate"],          {"ref": "demo_sig", "decision": "ACCEPT", "why": "tag=A"})
    run_append(paths["policy_change"], {"file": "gate_policy.yaml", "conf_accept": 0.60, "conf_abstain": 0.0})

    print("EMIT_DONE")
if __name__ == "__main__":
    main()
