#!/usr/bin/env python3
import json, time, subprocess, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
DASH = ROOT/"dashboards"/"metrics.json"

def run_one(sig_out: pathlib.Path):
    r = subprocess.run(["python3", str(ROOT/"scripts"/"rules_min.py"),
                        str(ROOT/"samples"/"features"/"valid"/"one.json")],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    sig_out.write_text(r.stdout)
    g = subprocess.run([str(ROOT/"scripts"/"emit_signal.sh"), str(sig_out)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    decision = "UNKNOWN"
    if "ACCEPT:" in g.stdout: decision = "ACCEPT"
    elif "ABSTAIN:" in g.stdout: decision = "ABSTAIN"
    elif "REJECT:" in g.stdout: decision = "REJECT"
    subprocess.run(["python3", str(ROOT/"scripts"/"deliver.py"), str(sig_out)],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    return decision

def main(duration_s=30):
    start = time.time()
    totals = {"ACCEPT":0,"ABSTAIN":0,"REJECT":0,"ALL":0}
    sig_path = ROOT/"tmp_sig_capacity.json"
    while time.time() - start < duration_s:
        d = run_one(sig_path)
        totals[d] = totals.get(d,0)+1
        totals["ALL"] += 1
    elapsed = max(1e-6, time.time() - start)
    rate_per_min = totals["ALL"] / (elapsed/60.0)
    try:
        m = json.load(open(DASH))
    except Exception:
        m = {"date": time.strftime("%Y%m%d")}
    m["emit_rate_per_min"] = round(rate_per_min, 3)
    m["daily_count_total"] = int(round(rate_per_min * 60 * 24))
    m["accepts"] = totals["ACCEPT"]
    m["abstains"] = totals["ABSTAIN"]
    m["rejects"] = totals["REJECT"]
    json.dump(m, open(DASH,"w"), indent=2)
    print("CAP_PROBE", json.dumps({"window_s": duration_s, "rate_per_min": round(rate_per_min,3), "totals": totals}))
if __name__=="__main__":
    dur = int(sys.argv[1]) if len(sys.argv)>1 else 30
    main(dur)
