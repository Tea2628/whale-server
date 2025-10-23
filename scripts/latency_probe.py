#!/usr/bin/env python3
import json, time, subprocess, pathlib, statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
DASH = ROOT/"dashboards"/"metrics.json"
HIST = ROOT/"dashboards"/"latency_history.jsonl"

def run_once():
    t0 = time.time()
    # 1) 生成 features -> signal
    sig_path = ROOT/"tmp_sig_probe.json"
    r = subprocess.run(["python3", str(ROOT/"scripts"/"rules_min.py"),
                        str(ROOT/"samples"/"features"/"valid"/"one.json")],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    with open(sig_path, "w") as f: f.write(r.stdout)
    # 2) gate（保留你现有 gate；若有 wrapper 也可替换）
    subprocess.run([str(ROOT/"scripts"/"emit_signal.sh"), str(sig_path)],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    # 3) deliver（file + telegram-stub）
    subprocess.run(["python3", str(ROOT/"scripts"/"deliver.py"), str(sig_path)],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    t1 = time.time()
    return (t1 - t0) * 1000.0

def quantile(vals, q):
    if not vals: return None
    vals = sorted(vals); idx = (len(vals)-1)*q
    lo, hi = int(idx), min(int(idx)+1, len(vals)-1)
    frac = idx - lo
    return vals[lo]*(1-frac) + vals[hi]*frac

def main(iters=10, sleep_s=0.0):
    samples=[]
    for i in range(iters):
        ms = run_once()
        samples.append(ms)
        with open(HIST, "a") as f:
            f.write(json.dumps({"ts": int(time.time()*1000), "latency_ms": round(ms,2)})+"\n")
        if sleep_s>0: time.sleep(sleep_s)
    p50 = quantile(samples, 0.5)
    p95 = quantile(samples, 0.95)
    summary = {"p50_ms": round(p50,2), "p95_ms": round(p95,2), "n": len(samples)}
    # 更新 dashboards/metrics.json 里的 latency_p95_ms
    try:
        m = json.load(open(DASH))
    except Exception:
        m = {"date": time.strftime("%Y%m%d"), "daily_count_total": 0,
             "abstain_ratio": "n/a", "gate_reject_total": "n/a",
             "emit_rate_per_min": "n/a", "latency_p95_ms": "n/a",
             "accepts": "n/a", "abstains": "n/a", "rejects": "n/a"}
    m["latency_p95_ms"] = summary["p95_ms"]
    json.dump(m, open(DASH, "w"), indent=2)
    print("LAT_PROBE", json.dumps(summary))
if __name__=="__main__":
    main()
