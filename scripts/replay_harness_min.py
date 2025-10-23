#!/usr/bin/env python3
import json, pathlib, time, math, statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVID = ROOT/"evidence"
AUD  = ROOT/"audit"/"audit.jsonl"
DASH = ROOT/"dashboards"/"metrics.json"

def load(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def read_jsonl(p: pathlib.Path):
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try:
                yield json.loads(line)
            except Exception:
                continue

def ci95(xs):
    if not xs: return ("n/a","n/a")
    m = st.mean(xs)
    if len(xs) < 2: return (m, "n/a")
    sd = st.pstdev(xs) if len(xs) > 30 else st.stdev(xs)
    se = sd / math.sqrt(len(xs))
    lo, hi = m - 1.96*se, m + 1.96*se
    return (lo, hi)

def main():
    dt = time.strftime("%Y%m%d", time.localtime())
    mani = ROOT/f"manifest/dt={dt}/manifest.json"
    mani_obj = load(mani)
    if not mani_obj:
        print(f"[ERR] manifest missing for dt={dt}: {mani}")
        return 2

    # 读取今天 ledger 中 signals 与 gate 两类分区（其余先不统计）
    sig_files = [ROOT/f["path"] for f in mani_obj.get("files", []) if "/signals/" in f["path"]]
    gate_files = [ROOT/f["path"] for f in mani_obj.get("files", []) if "/gate/" in f["path"]]

    sig_cnt = 0
    exp_pnls = []
    for p in sig_files:
        for obj in read_jsonl(p):
            sig_cnt += 1
            v = obj.get("expected_pnl")
            if isinstance(v,(int,float)): exp_pnls.append(float(v))

    gate_cnt = 0
    gate_accept = 0
    gate_abstain = 0
    gate_reject = 0
    for p in gate_files:
        for obj in read_jsonl(p):
            gate_cnt += 1
            x = (obj.get("decision") or obj.get("explain") or [])
            # 兼容我们之前的“解释串”风格：包含 ACCEPT/abstain/reject 关键词
            s = " ".join(x) if isinstance(x, list) else str(x)
            s_low = s.lower()
            if "accept" in s_low:
                gate_accept += 1
            elif "abstain" in s_low:
                gate_abstain += 1
            elif "reject" in s_low:
                gate_reject += 1

    # OPE 指标（极简版）
    mean_pnl = (st.mean(exp_pnls) if exp_pnls else "n/a")
    lo, hi  = ci95(exp_pnls)
    coverage = {
        "signals": sig_cnt,
        "gate_total": gate_cnt,
        "gate_accept": gate_accept,
        "gate_abstain": gate_abstain,
        "gate_reject": gate_reject
    }
    report = {
        "date": dt,
        "source_manifest": f"manifest/dt={dt}/manifest.json",
        "coverage": coverage,
        "metrics": {
            "expected_pnl_avg": mean_pnl,
            "expected_pnl_ci95": [lo, hi],
        },
        "notes": "minimal OPE over expected_pnl only"
    }

    # 落地 OPE 报告
    out_dir = EVID/"ope_report"
    out_dir.mkdir(parents=True, exist_ok=True)
    outp = out_dir/f"{dt}_ope_report.json"
    with open(outp,"w",encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 质量卡（极简门限：accept 覆盖>0 & mean_pnl 非负 => pass；否则 warn/fail）
    verdict = "pass"
    reason  = []
    if coverage["gate_accept"] <= 0:
        verdict = "fail"; reason.append("no_accepts")
    if mean_pnl != "n/a" and mean_pnl < 0:
        verdict = "warn" if verdict=="pass" else verdict
        reason.append("mean_expected_pnl<0")

    qc = {
        "date": dt,
        "verdict": verdict,
        "reasons": reason,
        "from_ope_report": str(outp.relative_to(ROOT)),
        "criteria": {
            "need_accepts_min": 1,
            "expected_pnl_avg_min": 0.0
        }
    }
    qc_dir = EVID/"quality_card"
    qc_dir.mkdir(parents=True, exist_ok=True)
    qc_out = qc_dir/f"{dt}_quality_card.json"
    with open(qc_out, "w", encoding="utf-8") as f:
        json.dump(qc, f, ensure_ascii=False, indent=2)

    # 更新 dashboards（只追加一个字段）
    try:
        dash = load(DASH) or {"date": dt}
    except Exception:
        dash = {"date": dt}
    dash["quality_gate_verdict"] = {"date": dt, "verdict": verdict, "reasons": reason}
    with open(DASH, "w", encoding="utf-8") as f:
        json.dump(dash, f, ensure_ascii=False, indent=2)

    # 审计
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD,"a",encoding="utf-8") as f:
        f.write(json.dumps({
            "event":"ope_report_make", "ts": int(time.time()*1000),
            "actor":"service","ref":dt,
            "explain":[f"ope_report -> {str(outp)}"]
        }, ensure_ascii=False)+"\n")
        f.write(json.dumps({
            "event":"quality_card_make", "ts": int(time.time()*1000),
            "actor":"service","ref":dt,
            "explain":[f"quality_card -> {str(qc_out)}", f"verdict={verdict}", *reason]
        }, ensure_ascii=False)+"\n")

    print(f"OPE_REPORT -> {outp}")
    print(f"QUALITY_CARD -> {qc_out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
