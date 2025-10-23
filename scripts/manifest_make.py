#!/usr/bin/env python3
import pathlib, hashlib, json, time

ROOT   = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT/"ledger"
MANI   = ROOT/"manifest"
AUD    = ROOT/"audit"/"audit.jsonl"

def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def record_cnt(p: pathlib.Path) -> int:
    with open(p, "rb") as f: return sum(1 for _ in f)

def main():
    today = time.strftime("%Y%m%d", time.localtime())
    items = []
    for p in LEDGER.rglob("*.jsonl"):
        # 只纳入今天 dt=YYYYMMDD 的分区
        if f"dt={today}" not in str(p): 
            if p.parent.name == f"dt={today}": pass
            else: continue
        items.append({
            "path": str(p.relative_to(ROOT)),
            "sha256": sha256_of(p),
            "record_cnt": record_cnt(p)
        })

    out_dir = MANI/f"dt={today}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir/"manifest.json"
    obj = {"date": today, "files": items, "total_files": len(items), "generated_ts": int(time.time()*1000)}
    json.dump(obj, open(out,"w"), ensure_ascii=False, indent=2)
    print(f"MANIFEST -> {out}")

    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD,"a") as f:
        f.write(json.dumps({
            "event":"manifest_make",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": today,
            "explain":[f"manifest built for dt={today} -> {str(out)}", f"files={len(items)}"]
        }, ensure_ascii=False)+"\n")

if __name__ == "__main__":
    main()
