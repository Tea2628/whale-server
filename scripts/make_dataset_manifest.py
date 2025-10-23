#!/usr/bin/env python3
import json, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC  = ROOT/"manifest"
OUTD = ROOT/"evidence"/"dataset_manifest"
AUD  = ROOT/"audit"/"audit.jsonl"

def main():
    today = time.strftime("%Y%m%d", time.localtime())
    src = SRC/f"dt={today}"/"manifest.json"
    if not src.exists():
        print(f"[ERR] missing {src}")
        raise SystemExit(2)

    mani = json.load(open(src))
    files = mani.get("files", [])
    total_files   = len(files)
    total_records = sum(int(x.get("record_cnt",0)) for x in files)

    dataset_manifest = {
        "date": today,
        "source_manifest": str(src.relative_to(ROOT)),
        "total_files": total_files,
        "total_records": total_records,
        "files": [
            {"path": f["path"], "sha256": f.get("sha256"), "record_cnt": int(f.get("record_cnt",0))}
            for f in files
        ],
        "generated_ts": int(time.time()*1000)
    }

    OUTD.mkdir(parents=True, exist_ok=True)
    outp = OUTD/f"{today}_dataset_manifest.json"
    json.dump(dataset_manifest, open(outp,"w"), ensure_ascii=False, indent=2)

    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD,"a") as f:
        f.write(json.dumps({
            "event":"dataset_manifest_make",
            "ts": dataset_manifest["generated_ts"],
            "actor":"service",
            "ref": today,
            "explain":[f"from {str(src)} -> {str(outp)}",
                       f"files={total_files}", f"records={total_records}"]
        }, ensure_ascii=False)+"\n")

    print(f"DATASET_MANIFEST -> {outp}")
if __name__ == "__main__": main()
