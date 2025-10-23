#!/usr/bin/env python3
import json, pathlib, time

ROOT=pathlib.Path(__file__).resolve().parents[1]
EVID_QC=ROOT/"evidence"/"quality_card"
POL =ROOT/"policies"/"gate_policy.yaml"
AUD =ROOT/"audit"/"audit.jsonl"
DASH=ROOT/"dashboards"/"metrics.json"

def add_audit(ev, ref, explain=None, meta=None):
    with open(AUD,"a") as f:
        f.write(json.dumps({"event":ev,"ts":int(time.time()*1000),"actor":"service","ref":ref, **({"explain":explain} if explain else {}), **({"meta":meta} if meta else {})}, ensure_ascii=False)+"\n")

def main():
    import yaml
    dt=time.strftime("%Y%m%d", time.localtime())
    qc = EVID_QC/f"{dt}_quality_card.json"
    if not qc.exists():
        print("NO_QUALITY_CARD"); return 0
    try:
        data=json.load(open(qc))
    except Exception as e:
        add_audit("quality_gate_enforce", dt, ["quality_card parse error"], {"error":str(e)})
        print("QUALITY_CARD_PARSE_ERROR"); return 1

    decision=data.get("decision")
    verdict =data.get("verdict","pass")
    t0=time.time()

    if decision in ("rollback","restrict") or verdict!="pass":
        y=yaml.safe_load(open(POL)) if POL.exists() else {"policy":{}}
        before=y.get("policy",{}).get("conf_accept","n/a")
        y.setdefault("policy",{})["conf_accept"]=0.90
        open(POL,"w").write(yaml.safe_dump(y, sort_keys=False))
        ms=int((time.time()-t0)*1000)
        add_audit("experiment_phase", "exp_auto", ["experiment exp_auto -> rolled_back"], {"reason":"quality_gate"})
        add_audit("template_apply", "auto", [f"apply_template -> gate_policy.yaml (conf_accept=0.9)"])
        try: dash=json.load(open(DASH))
        except: dash={}
        dash["whale_rollback_latency_ms"]=ms
        json.dump(dash, open(DASH,"w"), ensure_ascii=False, indent=2)
        add_audit("quality_gate_enforce", dt, [f"rollback decision={decision} verdict={verdict}"], {"latency_ms":ms, "before":before, "after":0.90})
        print(f"ROLLBACK_ENFORCED latency_ms={ms}")
    else:
        add_audit("quality_gate_enforce", dt, ["no action (pass)"])
        print("NO_ACTION")
    return 0

if __name__=="__main__": main()
