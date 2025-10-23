#!/usr/bin/env python3
import json, sys, pathlib
from jsonschema import Draft7Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT/"schemas/json"
SAMPLES_DIR = ROOT/"samples"

# 1) 自动发现所有 *.schema.json → SCHEMA 映射
SCHEMA = {}
for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
    kind = p.name.replace(".schema.json","")
    try:
        SCHEMA[kind] = json.load(open(p))
    except Exception as e:
        print(f"[ERROR] schema load failed: {p}: {e}", file=sys.stderr)

def check(kind: str):
    ok = bad = 0
    schema = SCHEMA.get(kind)
    if not schema:
        print(f"[SKIP] {kind}: schema not found")
        return ok, bad
    validator = Draft7Validator(schema)
    for bucket in ("valid","edge","invalid"):
        d = SAMPLES_DIR/kind/bucket
        if not d.exists(): 
            print(f"[SKIP] {kind}: samples/{kind}/{bucket} missing")
            continue
        for f in sorted(d.glob("*.json")):
            data = json.load(open(f))
            errs = sorted(validator.iter_errors(data), key=lambda e: e.path)
            if errs:
                print(f"[FAIL] {kind}: {f.relative_to(ROOT)}")
                for e in errs:
                    print(f"  - {e.message}")
                bad += 1
            else:
                print(f"[OK]   {kind}: {f.relative_to(ROOT)}")
                ok += 1
    return ok, bad

def main():
    kinds = sorted(SCHEMA.keys())
    # 允许旧清单中的 5 类即使目录缺失也不失败
    baseline = ["features","gpt_suggestion","signal","gateway_attempt","audit"]
    for k in baseline:
        if k not in kinds: kinds.append(k)
    OK = BAD = 0
    print("== B-Stage Validator ==")
    for k in kinds:
        o, b = check(k); OK += o; BAD += b
    print("\n=== SUMMARY ===")
    print(f"OK={OK} BAD={BAD}")

if __name__=="__main__":
    main()
