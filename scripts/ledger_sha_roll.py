#!/usr/bin/env python3
import pathlib, subprocess, time, json, sys

ROOT   = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT/"ledger"
AUD    = ROOT/"audit"/"audit.jsonl"

def sha_and_records(jsonl_path: pathlib.Path):
    d = jsonl_path.parent
    sha_out = subprocess.run(["sha256sum", jsonl_path.name], cwd=d, capture_output=True, text=True, check=True).stdout
    (d/"SHA256SUMS").write_text(sha_out)
    cnt = sum(1 for _ in open(jsonl_path, "rb"))
    (d/"RECORDS").write_text(f"{jsonl_path.name} {cnt}\n")

def main():
    today = time.strftime("%Y%m%d", time.localtime())
    processed_dirs = 0

    # 遍历 ledger/*，不写死目录名；兼容 dt=YYYYMMDD[/symbol=XXX]/HH.jsonl 结构
    for first in sorted(LEDGER.glob("*")):
        if not first.is_dir(): continue
        # policy_change 没有 symbol= 子目录，其他通常有
        for dtp in sorted(first.glob(f"dt={today}")):
            # 可能有 symbol=XXX 层
            jsonl_files = list(dtp.glob("*.jsonl"))
            if not jsonl_files:
                for sym in sorted(dtp.glob("symbol=*")):
                    jsonl_files += list(sym.glob("*.jsonl"))
            for jf in jsonl_files:
                sha_and_records(jf)
                processed_dirs += 1

    # 审计
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD, "a") as f:
        f.write(json.dumps({
            "event":"ledger_sha_roll",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": today,
            "explain":[f"hour={time.strftime('%H')}", f"dirs={processed_dirs}"]
        })+"\n")
    print(f"SHA_ROLL ok hour={time.strftime('%H')} dirs={processed_dirs}")

if __name__ == "__main__":
    sys.exit(main() or 0)
