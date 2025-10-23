#!/usr/bin/env python3
import json, sys, time, pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
POL  = ROOT/"policies"/"gate_policy.yaml"
AUD  = ROOT/"audit"/"audit.jsonl"

def append_audit(ev):
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD, "a") as f:
        f.write(json.dumps(ev, ensure_ascii=False)+"\n")

def main():
    if len(sys.argv) < 2:
        print("usage: apply_template.py <template.json>"); sys.exit(2)
    tpl_path = pathlib.Path(sys.argv[1])
    tpl = json.load(open(tpl_path))

    name = tpl.get("name") or tpl.get("id") or tpl_path.stem
    params = tpl.get("params") or {}
    conf_accept  = float(params.get("conf_accept", 0.60))
    conf_abstain = float(params.get("conf_abstain", 0.00))

    POL.parent.mkdir(parents=True, exist_ok=True)
    yaml.safe_dump({"policy":{"conf_accept":conf_accept,"conf_abstain":conf_abstain}}, open(POL,"w"))

    ev = {
        "event":"template_apply",
        "ts": int(time.time()*1000),
        "actor":"service",
        "ref": name,
        "explain":[f"apply_template -> gate_policy.yaml (conf_accept={conf_accept}, conf_abstain={conf_abstain})"]
    }
    append_audit(ev)
    print(f"APPLIED template='{name}' -> conf_accept={conf_accept} conf_abstain={conf_abstain}")

if __name__=="__main__":
    main()
