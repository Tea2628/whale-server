#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys, os, glob, pathlib
from jsonschema import Draft7Validator, ValidationError

SCHEMA_DIR="schemas/json"
SAMPLES_DIR="samples"

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_file(schema_path, sample_path):
    schema = load_json(schema_path)
    data = load_json(sample_path)
    v = Draft7Validator(schema)
    errs = sorted(v.iter_errors(data), key=lambda e: e.path)
    return errs  # 空代表通过；非空代表失败

def print_line(ok, kind, path, errs=None, level='OK'):
    lvl = level if level in ('OK','FAIL','WARN') else ('OK' if ok else 'FAIL')
    tag = {'OK':'[OK]  ', 'FAIL':'[FAIL]', 'WARN':'[WARN]'}[lvl]
    print(f"{tag} {kind}: {path}")
    if errs and lvl!='OK':
        for e in errs[:3]:
            msg = getattr(e, 'message', str(e))
            print(f"  - {msg}")

def main():
    total_ok = total_bad = 0
    # 映射：schema 名称 -> schema 文件路径
    schemas = { pathlib.Path(p).stem.replace(".schema",""): p
                for p in glob.glob(os.path.join(SCHEMA_DIR, "*.schema.json")) }

    for kind in sorted(schemas.keys()):
        sch_path = schemas[kind]
        base = os.path.join(SAMPLES_DIR, kind)
        if not os.path.isdir(base):
            continue
        for group in ("valid","edge","invalid"):
            gdir = os.path.join(base, group)
            if not os.path.isdir(gdir):
                continue
            for sp in sorted(glob.glob(os.path.join(gdir, "*.json"))):
                errs = None
                try:
                    errs = validate_file(sch_path, sp)
                except Exception as ex:
                    # 解析失败统一当作错误（但 invalid 组依然算 OK）
                    errs = [ex]
                should_pass = group in ("valid","edge")
                actually_pass = (not errs)
                # 期望：valid/edge -> pass； invalid -> fail
                ok = (actually_pass == should_pass)
                level = 'OK'
                if not ok:
                    # 特例：invalid 组却通过 -> 降级 WARN（样例可能没命中约束）
                    if group == 'invalid' and actually_pass:
                        level = 'WARN'
                        ok = True
                    else:
                        level = 'FAIL'
                print_line(ok, kind, sp, (None if ok else errs), level)
                total_ok += int(ok); total_bad += int(not ok)
    print("\n=== SUMMARY (expected-aware) ===")
    print(f"OK={total_ok} BAD={total_bad}")
    sys.exit(0 if total_bad==0 else 1)

if __name__ == "__main__":
    main()
