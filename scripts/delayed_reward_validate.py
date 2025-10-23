#!/usr/bin/env python3
import json, time, pathlib, sys
from jsonschema import Draft7Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.load(open(ROOT/"schemas"/"json"/"delayed_reward_ledger.schema.json"))
AUD = ROOT/"audit"/"audit.jsonl"
LEDG = ROOT/"ledger"

def jlines(p):
    with open(p, "rb") as f:
        for i,line in enumerate(f,1):
            if not line.strip(): continue
            yield i, json.loads(line)

def main():
    dt = time.strftime("%Y%m%d", time.localtime())
    errs, ok = 0, 0
    files = []

    base = LEDG/"delayed_reward_ledger"/f"dt={dt}"
    if base.exists():
        for p in sorted(base.rglob("*.jsonl")):
            files.append(str(p))
            for ln, rec in jlines(p):
                e = sorted(Draft7Validator(SCHEMA).iter_errors(rec), key=lambda e: e.path)
                if e:
                    errs += 1
                    print(f"VALIDATE_FAIL {p}:{ln} -> {e[0].message}")
                else:
                    ok += 1

    with open(AUD,"a") as f:
        f.write(json.dumps({
            "event":"delayed_reward_validate",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": dt,
            "meta":{"files": len(files), "ok": ok, "errs": errs},
            "explain":[f"validated delayed_reward_ledger dt={dt}"]
        })+"\n")

    if errs==0:
        print(f"[OK] delayed_reward_ledger valid (files={len(files)} lines={ok})")
        sys.exit(0)
    else:
        print(f"[FAIL] delayed_reward_ledger errors={errs} (files={len(files)} ok_lines={ok})")
        sys.exit(1)

if __name__ == "__main__":
    main()
