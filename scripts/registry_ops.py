#!/usr/bin/env python3
import json, time, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
AUD  = ROOT/"audit"/"audit.jsonl"
def append(ev):
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD, "a") as f: f.write(json.dumps(ev, ensure_ascii=False)+"\n")
def now(): return int(time.time()*1000)
def main():
    if len(sys.argv)<3: print("usage: registry_ops.py <action> <name> [meta_json]"); sys.exit(2)
    action, name = sys.argv[1], sys.argv[2]
    meta = json.loads(sys.argv[3]) if len(sys.argv)>3 else {}
    m = {"preview":"registry_preview","commit":"registry_update","revoke":"registry_revoke"}.get(action)
    if not m: print("unknown action", action); sys.exit(2)
    append({"event":m,"ts":now(),"actor":"service","ref":name,"meta":meta,"explain":[f"{action} {name}"]})
    print(f"REGISTRY {action.upper()} {name}")
if __name__=="__main__": main()
