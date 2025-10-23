#!/usr/bin/env python3
import json, time, subprocess, pathlib, sys, yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
POL  = ROOT/"policies"/"gate_policy.yaml"
WRAP = ROOT/"scripts"/"gate_policy_wrapper.py"
SIG  = ROOT/"tmp_sig_reload.json"
DASH = ROOT/"dashboards"/"metrics.json"

def write_policy(conf_accept: float):
    POL.parent.mkdir(parents=True, exist_ok=True)
    yaml.safe_dump({"policy":{"conf_accept": float(conf_accept), "conf_abstain": 0.0}}, open(POL, "w"))

def make_signal():
    out = subprocess.run(["python3", str(ROOT/"scripts"/"rules_min.py"), str(ROOT/"samples"/"features"/"valid"/"one.json")],
                         stdout=subprocess.PIPE, text=True, cwd=ROOT)
    SIG.write_text(out.stdout)

def decide():
    out = subprocess.run(["python3", str(WRAP), str(SIG)], stdout=subprocess.PIPE, text=True, cwd=ROOT)
    s = out.stdout.strip()
    if "ABSTAIN" in s: return "ABSTAIN"
    if "ACCEPT"  in s: return "ACCEPT"
    if "REJECT"  in s: return "REJECT"
    return "UNKNOWN"

def wait_until(target, timeout_s=2.5):
    t0 = time.time()
    while time.time() - t0 <= timeout_s:
        if decide() == target:
            return int((time.time()-t0)*1000)
        # 轻微退避，保证≤2.5s窗口内多次探测
        time.sleep(0.02)
    return None

def update_metrics(max_latency_ms):
    try: m = json.load(open(DASH))
    except: m = {"date": time.strftime("%Y%m%d")}
    m["whale_policy_reload_latency_ms"] = max_latency_ms
    json.dump(m, open(DASH,"w"), indent=2)

def main():
    make_signal()
    # 严格→应 ABSTAIN
    write_policy(0.90)
    t1 = wait_until("ABSTAIN", timeout_s=2.5)
    # 宽松→应 ACCEPT
    write_policy(0.60)
    t2 = wait_until("ACCEPT", timeout_s=2.5)

    ok = (t1 is not None) and (t2 is not None)
    maxlat = max(t for t in [t1 or 9999, t2 or 9999])
    if ok: update_metrics(maxlat)
    print("RELOAD_PROBE", json.dumps({"strict_ms": t1, "relax_ms": t2, "ok": ok, "max_ms": maxlat}))
    sys.exit(0 if ok else 1)

if __name__=="__main__":
    main()
