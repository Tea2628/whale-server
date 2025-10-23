#!/usr/bin/env python3
import json, time, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
AUD  = ROOT/"audit"/"audit.jsonl"
def append(ev):
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD, "a") as f: f.write(json.dumps(ev, ensure_ascii=False)+"\n")
def now(): return int(time.time()*1000)
def main():
    if len(sys.argv)<3: print("usage: experiment_flow.py <exp_id> <phase> [meta_json]"); sys.exit(2)
    exp, phase = sys.argv[1], sys.argv[2].lower()
    meta = json.loads(sys.argv[3]) if len(sys.argv)>3 else {}
    allowed = ["shadow","canary","promoted","rolled_back"]
    if phase not in allowed: print("bad phase", phase); sys.exit(2)
    append({"event":"experiment_phase","ts":now(),"actor":"service","ref":exp,"phase":phase,"meta":meta,"explain":[f"experiment {exp} -> {phase}"]})
    print(f"EXPERIMENT {exp} {phase}")
if __name__=="__main__": main()
