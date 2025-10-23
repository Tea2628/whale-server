#!/usr/bin/env python3
import json, sys, time, pathlib, shutil, subprocess
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONF = ROOT/"config"/"gate.yml"
AUDIT = ROOT/"audit"/"audit.jsonl"

def append_audit(ref, msg):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT, "a") as f:
        f.write(json.dumps({"event":"deliver","ref":ref,"ts":int(time.time()*1000),
                            "actor":"service","explain":[msg]}, ensure_ascii=False)+"\n")

def deliver_file(sig_path: pathlib.Path, out_root: pathlib.Path):
    ts = time.strftime("%Y%m%d")
    out_dir = out_root/ts
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir/sig_path.name
    shutil.copy2(sig_path, dst)
    append_audit(sig_path.stem, f"deliver:file -> {dst}")
    return dst

def deliver_telegram_stub(sig_path: pathlib.Path):
    logp = ROOT/"logs"/"telegram.log"
    try:
        subprocess.run([sys.executable, str(ROOT/"scripts"/"telegram_stub.py"), str(sig_path)],
                       check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    finally:
        append_audit(sig_path.stem, f"deliver:telegram stub -> {logp}")
    return logp

def main():
    if len(sys.argv) < 2:
        print("usage: deliver.py <signal_json_file>"); sys.exit(2)
    sig_path = pathlib.Path(sys.argv[1]).resolve()
    if not sig_path.exists(): 
        print(f"no such file: {sig_path}"); sys.exit(3)

    cfg = yaml.safe_load(open(CONF)) if CONF.exists() else {"deliver":{"file":{"enabled":True,"out_dir":"release"}}}
    file_cfg = ((cfg or {}).get("deliver",{}).get("file",{}))
    tg_cfg = ((cfg or {}).get("deliver",{}).get("telegram",{}))

    delivered = []
    if file_cfg.get("enabled", True):
        out_root = ROOT/file_cfg.get("out_dir","release")
        delivered.append(str(deliver_file(sig_path, out_root)))
    if tg_cfg.get("enabled", False):
        deliver_telegram_stub(sig_path)

    if delivered:
        print("DELIVERED:", ";".join(delivered)); sys.exit(0)
    else:
        print("SKIPPED: all channels disabled"); sys.exit(1)

if __name__ == "__main__":
    main()
