#!/usr/bin/env python3
import json, pathlib, time, re, statistics as st, shutil, os, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
LEDGER=ROOT/"ledger"/"features"
AUD =ROOT/"audit"/"audit.jsonl"
DASH=ROOT/"dashboards"/"metrics.json"
num_re = re.compile(r'[-+]?\d+\.?\d*(?:e[-+]?\d+)?', re.I)

def parse_line(line:str):
    return [float(x) for x in num_re.findall(line)]

def snapshot_stats(p):
    vals=[]
    with open(p,"r",encoding="utf-8") as f:
        for line in f: vals += parse_line(line)
    if not vals: return {"n":0}
    return {"n":len(vals),"mean":st.mean(vals),"stdev":(st.stdev(vals) if len(vals)>1 else 0.0)}

def add_audit(ev, ref, explain=None, meta=None):
    with open(AUD,"a") as f:
        f.write(json.dumps({"event":ev,"ts":int(time.time()*1000),"actor":"service","ref":ref, **({"explain":explain} if explain else {}), **({"meta":meta} if meta else {})}, ensure_ascii=False)+"\n")

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--bootstrap-prev", action="store_true", help="没有上一小时数据时，用当前小时复制一份作为 prev")
    ap.add_argument("--symbol", default="BTCUSDT")
    args=ap.parse_args()

    dt=time.strftime("%Y%m%d", time.localtime())
    hh=int(time.strftime("%H"))
    cur=LEDGER/f"dt={dt}"/f"symbol={args.symbol}"/f"{hh:02d}.jsonl"
    prev=LEDGER/f"dt={dt}"/f"symbol={args.symbol}"/f"{hh-1:02d}.jsonl"

    if not cur.exists():
        print("DRIFT_SKIP: no current hour file"); return 0
    if not prev.exists():
        if args.bootstrap_prev:
            shutil.copy2(cur, prev)
        else:
            print("DRIFT_SKIP"); return 0

    s1=snapshot_stats(prev); s2=snapshot_stats(cur)
    if s1.get("n",0)<10 or s2.get("n",0)<10:
        print("DRIFT_INSUFF_DATA"); return 0

    def rel(a,b): 
        if a==0: return 0 if b==0 else 1e9
        return abs(b-a)/max(1e-12,abs(a))
    r_mean=rel(s1["mean"], s2["mean"]); r_std=rel(s1["stdev"], s2["stdev"])
    drift = (r_mean>0.5 or r_std>0.5)
    meta={"prev":s1,"curr":s2,"r_mean":r_mean,"r_std":r_std,"drift":drift}

    if drift:
        add_audit("drift_alert", dt, ["features distribution shift"], meta)
        try: dash=json.load(open(DASH))
        except: dash={}
        dd=dash.get("whale_drift_alerts_total",{}); dd["features"]=int(dd.get("features",0))+1; dash["whale_drift_alerts_total"]=dd
        json.dump(dash, open(DASH,"w"), ensure_ascii=False, indent=2)
        print("DRIFT_ALERT")
    else:
        print("DRIFT_OK")
    return 0

if __name__=="__main__": sys.exit(main() or 0)
