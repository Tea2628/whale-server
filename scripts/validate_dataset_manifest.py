#!/usr/bin/env python3
import json, time, pathlib, sys
from jsonschema import Draft7Validator

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT/"schemas"/"json"/"dataset_manifest.schema.json"
EVID   = ROOT/"evidence"/"dataset_manifest"
AUD    = ROOT/"audit"/"audit.jsonl"

def main():
    today = time.strftime("%Y%m%d", time.localtime())
    inp = EVID/f"{today}_dataset_manifest.json"
    schema = json.load(open(SCHEMA))
    obj    = json.load(open(inp))

    v = Draft7Validator(schema)
    errs = sorted(v.iter_errors(obj), key=lambda e: e.path)
    if errs:
        print("[FAIL] dataset_manifest not valid:")
        for e in errs:
            loc = ".".join([str(x) for x in e.path]) or "<root>"
            print(f"  - {loc}: {e.message}")
        ok = False
    else:
        print("[OK] dataset_manifest valid")
        ok = True

    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD,"a") as f:
        f.write(json.dumps({
            "event":"dataset_manifest_validate",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": today,
            "explain":[("valid" if ok else "invalid"), str(inp)]
        }, ensure_ascii=False)+"\n")

    sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
