#!/usr/bin/env python3
import json, sys, time, pathlib, subprocess, yaml
ROOT = pathlib.Path(__file__).resolve().parents[1]
CONF = ROOT/"config"/"gate_policy.yaml"
AUDIT = ROOT/"audit"/"audit.jsonl"
EMIT = ROOT/"scripts"/"emit_signal.sh"

def load_policy():
    ca, cb = 0.60, 0.58
    if CONF.exists():
        y = yaml.safe_load(open(CONF)) or {}
        pol = (y.get("policy") or {})
        ca = float(pol.get("conf_accept", ca))
        cb = float(pol.get("conf_abstain", cb))
    return max(0.0, min(1.0, ca)), max(0.0, min(1.0, cb))

def append_audit(ref, msg):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT, "a") as f:
        f.write(json.dumps({"event":"gate","ref":ref,"ts":int(time.time()*1000),
                            "actor":"service","explain":[msg]}, ensure_ascii=False)+"\n")

def main():
    if len(sys.argv) < 2:
        print("usage: gate_policy_wrapper.py <signal.json>"); sys.exit(2)
    p = pathlib.Path(sys.argv[1])
    sig = json.load(open(p))
    ref = sig.get("id","unknown")
    conf_accept, conf_abstain = load_policy()

    # 显式 abstain 直接拦截
    if sig.get("abstain") is True:
        print("ABSTAIN: flag")
        append_audit(ref, "Gate-Wrapper abstain: flag")
        sys.exit(0)

    # 置信度阈值前置判定
    conf = float(sig.get("conf", 0.0))
    if conf < conf_accept:
        print("ABSTAIN: policy_conf")
        append_audit(ref, f"Gate-Wrapper abstain: conf<{conf_accept}")
        sys.exit(0)

    # 放行到既有脚本（稳定路径）：emit_signal.sh
    try:
        out = subprocess.run([str(EMIT), str(p)], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, timeout=3, cwd=ROOT)
        s = out.stdout.strip()
        # 透传已有输出以兼容你的脚本生态
        print(s.splitlines()[-1] if s else "ACCEPT: ACCEPT")
    except subprocess.TimeoutExpired:
        print("ABSTAIN: gate_timeout")
        append_audit(ref, "Gate-Wrapper abstain: gate_timeout")
        sys.exit(0)

if __name__=="__main__":
    main()
