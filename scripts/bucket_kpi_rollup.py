#!/usr/bin/env python3
import json, time, pathlib, statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLES = ROOT/"samples"/"bucket_kpi"
EVID    = ROOT/"evidence"/"bucket_kpi"
DASH    = ROOT/"dashboards"/"metrics.json"
AUD     = ROOT/"audit"/"audit.jsonl"

def load_json(p):
    try:
        return json.load(open(p))
    except Exception:
        return None

def main():
    today = time.strftime("%Y%m%d", time.localtime())
    buckets = []

    # 仅聚合 valid 与 edge；invalid 只做失败通道验证，不统计
    for sub in ["valid","edge"]:
        d = SAMPLES/sub
        if not d.exists(): continue
        for p in sorted(d.glob("*.json")):
            obj = load_json(p)
            if not obj: continue
            buckets.append(obj)

    # 简单归并：累计各 bucket 的 accept/abstain/reject 与可用的 latency_p95_ms
    total = {"accepts":0, "abstains":0, "rejects":0, "buckets":0}
    lat_list = []
    merged = []

    for b in buckets:
        name = b.get("name") or b.get("bucket") or "unknown"
        a = int(b.get("accepts", 0))
        s = int(b.get("abstains", 0))
        r = int(b.get("rejects", 0))
        lat = b.get("latency_p95_ms", None)

        total["accepts"]  += a
        total["abstains"] += s
        total["rejects"]  += r
        total["buckets"]  += 1
        if isinstance(lat, (int,float)): lat_list.append(float(lat))

        merged.append({"bucket": name, "accepts": a, "abstains": s, "rejects": r, "latency_p95_ms": lat})

    rollup = {
        "date": today,
        "total": total,
        "latency_p95_ms_overall": (st.median(lat_list) if lat_list else "n/a"),
        "buckets": merged,
        "source": "samples/bucket_kpi(valid+edge)"
    }

    # 写 evidence
    EVID.mkdir(parents=True, exist_ok=True)
    outp = EVID/f"{today}_rollup.json"
    json.dump(rollup, open(outp,"w"), ensure_ascii=False, indent=2)

    # 兼容更新 dashboards/metrics.json（只添加 bucket_kpi_summary 字段）
    DASH.parent.mkdir(parents=True, exist_ok=True)
    try:
        dash = json.load(open(DASH))
    except Exception:
        dash = {"date": today}
    dash["bucket_kpi_summary"] = {
        "date": today,
        "buckets": total["buckets"],
        "accepts": total["accepts"],
        "abstains": total["abstains"],
        "rejects": total["rejects"],
        "latency_p95_ms_overall": rollup["latency_p95_ms_overall"]
    }
    json.dump(dash, open(DASH,"w"), ensure_ascii=False, indent=2)

    # 记审计
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD,"a") as f:
        f.write(json.dumps({
            "event":"bucket_kpi_rollup",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": today,
            "explain":[f"bucket_kpi aggregated from samples -> {str(outp)}"]
        }, ensure_ascii=False)+"\n")

    print(f"ROLLED_UP -> {outp}")
