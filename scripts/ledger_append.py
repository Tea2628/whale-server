#!/usr/bin/env python3
import sys, json, pathlib, time

def ensure_parent(p: pathlib.Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def append_jsonl(path: pathlib.Path, obj: dict):
    ensure_parent(path)
    with open(path, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False)+"\n")

def main():
    if len(sys.argv) != 3:
        print("USAGE: ledger_append.py <out_path.jsonl> '<json_object>'", file=sys.stderr)
        sys.exit(2)
    out = pathlib.Path(sys.argv[1])
    try:
        obj = json.loads(sys.argv[2])
    except Exception as e:
        print(f"bad json: {e}", file=sys.stderr); sys.exit(3)
    # 追加写 & 附加标准字段
    obj.setdefault("ts", int(time.time()*1000))
    append_jsonl(out, obj)
    print(f"APPENDED -> {out}")
if __name__ == "__main__":
    main()
