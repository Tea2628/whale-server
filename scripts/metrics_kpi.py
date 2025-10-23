#!/usr/bin/env python3
import json, time, pathlib, datetime, re
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUD = ROOT/"audit"/"audit.jsonl"
SIGDIR = ROOT/"signals"/time.strftime("%Y%m%d")
DEAD = ROOT/"dead_letter"
OUT = ROOT/"dashboards"/"metrics.json"

today = datetime.date.today().strftime("%Y%m%d")
now_ms = int(time.time()*1000)

def iter_audit_today():
    if not AUD.exists(): return []
    rows=[]
    with open(AUD) as f:
        for line in f:
            try:
                obj=json.loads(line)
                ts=obj.get("ts",0)
                d=datetime.datetime.utcfromtimestamp(ts/1000.0)
                if d.strftime("%Y%m%d")==today and obj.get("event")=="gate":
                    rows.append(obj)
            except Exception:
                pass
    return rows

def parse_kind(explain_list):
    msg=" ".join(explain_list or [])
    if "ACCEPT" in msg: return "ACCEPT"
    if "abstain" in msg.lower(): return "ABSTAIN"
    if "reject" in msg.lower(): return "REJECT"
    return "OTHER"

def kpis():
    audits = iter_audit_today()
    kinds = [parse_kind(a.get("explain")) for a in audits]
    c = Counter(kinds)
    total = sum(c[k] for k in ("ACCEPT","ABSTAIN","REJECT","OTHER"))
    total = max(total, 1)  # avoid div by zero

    # emit_rate: accepts per minute since first ACCEPT today
    first_accept_ts = None
    for a in audits:
        if parse_kind(a.get("explain"))=="ACCEPT":
            t=a.get("ts"); 
            if isinstance(t,int):
                first_accept_ts = t if first_accept_ts is None else min(first_accept_ts, t)
    minutes = 1
    if first_accept_ts:
        minutes = max(1, (now_ms - first_accept_ts)//60000)
    emit_rate = round(c["ACCEPT"]/minutes, 3)

    # latency_p95: read from any metrics.latency_ms_p95 if present; else "n/a"
    lat_vals=[]
    for a in audits:
        m=a.get("metrics") or {}
        v=m.get("latency_ms_p95")
        if isinstance(v,(int,float)): lat_vals.append(float(v))
    latency_p95 = (sorted(lat_vals)[int(0.95*len(lat_vals))-1] if lat_vals else "n/a")

    # rejects: by audit + dead_letter files today
    dead_count = 0
    if DEAD.exists():
        dead_count = len(list(DEAD.glob("*.json")))
    gate_reject_total = max(c["REJECT"], dead_count)  # 防止遗漏

    daily_count_total = total
    abstain_ratio = round(c["ABSTAIN"]/total, 3)

    return {
        "date": today,
        "daily_count_total": daily_count_total,
        "abstain_ratio": abstain_ratio,
        "gate_reject_total": gate_reject_total,
        "emit_rate_per_min": emit_rate,
        "latency_p95_ms": latency_p95,
        "accepts": c["ACCEPT"],
        "abstains": c["ABSTAIN"],
        "rejects": c["REJECT"]
    }

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = kpis()
    with open(OUT,"w") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    print("KPI_SUMMARY", json.dumps(data, ensure_ascii=False))

if __name__=="__main__":
    main()
