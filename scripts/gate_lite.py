#!/usr/bin/env python3
import json, sys, time, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
SC=ROOT/"schemas/json"/"signal.schema.json"
TODAY=ROOT/"signals"/time.strftime("%Y%m%d")
DEAD=ROOT/"dead_letter"
AUDIT=ROOT/"audit"/"audit.jsonl"

REQ=["id","ts","symbol","side","level","conf","ttl_s","abstain","reasons","policy_ref","contract_version"]

def append_audit(ref,msg):
  AUDIT.parent.mkdir(parents=True,exist_ok=True)
  with open(AUDIT,"a") as f:
    f.write(json.dumps({"event":"gate","ref":ref,"ts":int(time.time()*1000),"actor":"service","explain":[msg]},ensure_ascii=False)+"\n")


CONF = pathlib.Path(__file__).resolve().parents[1]/"config"/"gate_policy.yaml"
conf_accept_default = 0.60
conf_abstain_default = 0.58
def load_policy():
    if CONF.exists():
        try:
            y = yaml.safe_load(open(CONF))
            pol = (y or {}).get("policy", {})
            ca = float(pol.get("conf_accept", conf_accept_default))
            cb = float(pol.get("conf_abstain", conf_abstain_default))
            return max(0.0, min(1.0, ca)), max(0.0, min(1.0, cb))
        except Exception:
            pass
    return conf_accept_default, conf_abstain_default
    

def main():
  sig=json.load(sys.stdin)
  # 轻校验（字段必备 + 枚举范围），严格校验已由 validate_contracts 负责
  miss=[k for k in REQ if k not in sig]
  if miss or sig.get("side") not in ("buy","sell") or sig.get("level") not in ("A","B","C"):
    DEAD.mkdir(parents=True,exist_ok=True)
    out={"signal_id":sig.get("id","n/a"),"accept":False,"delivered":False,"deliver_channels":["file"],"retry_count":0,
         "reject_reason": ("missing:"+",".join(miss)) if miss else "enum"}
    with open(DEAD/f"dead_{sig.get('id','n')}.json","w") as f: json.dump(out,f)
    append_audit(sig.get("id","n/a"), "Gate-Lite reject")
    print("REJECT:", out["reject_reason"]); sys.exit(2)

  conf=float(sig.get("conf",0)); lvl=sig.get("level","C")
  if sig.get("abstain"): decision,tag="ABSTAIN","flagged"
  elif lvl=="A" and conf>=0.60: decision,tag="ACCEPT","A"
  elif lvl in ("A","B") and conf>=0.55: decision,tag="ACCEPT_SHADOW","B-shadow"
  else: decision,tag="ABSTAIN","low_conf"

  if decision.startswith("ACCEPT"):
    TODAY.mkdir(parents=True,exist_ok=True)
    with open(TODAY/f"{sig['id']}.json","w") as f: json.dump(sig,f)
    append_audit(sig["id"], f"Gate-Lite {decision} tag={tag}")
    print("ACCEPT:", decision); sys.exit(0)
  else:
    append_audit(sig["id"], f"Gate-Lite abstain: {tag}")
    print("ABSTAIN:", tag); sys.exit(1)

if __name__=="__main__": main()
