#!/usr/bin/env python3
import json, sys, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT/"logs"/"telegram.log"

def fmt(sig):
    return (f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"TG(STUB) id={sig.get('id')} symbol={sig.get('symbol')} "
            f"side={sig.get('side')} level={sig.get('level')} conf={sig.get('conf')}")

def main():
    if len(sys.argv)<2: 
        print("usage: telegram_stub.py <signal.json>"); sys.exit(2)
    sig = json.load(open(sys.argv[1]))
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(fmt(sig)+"\n")
    print("TELEGRAM_STUB:", LOG)
if __name__=="__main__":
    main()
