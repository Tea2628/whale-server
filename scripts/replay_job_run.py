#!/usr/bin/env python3
import json, time, pathlib, uuid, hashlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUD  = ROOT/"audit"/"audit.jsonl"
LEDG = ROOT/"ledger"
RJ_EVID = ROOT/"evidence"/"replay_job"

def today():
    return time.strftime("%Y%m%d", time.localtime())

def jlines(p):
    with open(p, "rb") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try:
                yield json.loads(line)
            except Exception:
                pass

def main():
    dt = today()
    jobp = RJ_EVID/f"{dt}_replay_job.json"
    job = json.load(open(jobp))
    job_id = job["job_id"]
    symbols = job.get("symbols", [])

    # 审计：start
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD, "a") as f:
        f.write(json.dumps({
            "event":"replay_job_start",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": job_id,
            "meta":{"dt": dt, "symbols": symbols},
            "explain":[f"start replay from {str(jobp)}"]
        })+"\n")

    total_in, total_out = 0, 0
    out_files = []

    # 扫描当天每个 symbol 的 signals 分区（所有小时）
    for sym in symbols:
        base = LEDG/"signals"/f"dt={dt}"/f"symbol={sym}"
        if not base.exists(): continue
        for sigf in sorted(base.glob("*.jsonl")):
            # 读取每条 signal，做一个“延迟奖励”占位标签（最小闭环）
            out_dir = LEDG/"delayed_reward_ledger"/f"dt={dt}"/f"symbol={sym}"
            out_dir.mkdir(parents=True, exist_ok=True)
            outp = out_dir/sigf.name
            wrote = 0
            with open(outp, "a") as wf:
                for rec in jlines(sigf):
                    total_in += 1
                    # ref 优先用 id；没有则用 sha1(line)
                    ref = rec.get("id") or hashlib.sha1(json.dumps(rec, sort_keys=True).encode()).hexdigest()[:12]
                    conf = float(rec.get("conf", 0.0))
                    # 极简规则：conf>=0.6 → pos；0.4~0.6 → neutral；否则 neg（只是占位）
                    if conf >= 0.6: label="pos"; realized=0.1
                    elif conf >= 0.4: label="neutral"; realized=0.0
                    else: label="neg"; realized=-0.1
                    out = {
                        "ref": ref,
                        "symbol": sym,
                        "ts": rec.get("ts"),
                        "delay_s": 1800,
                        "realized_pnl": realized,
                        "label": label
                    }
                    wf.write(json.dumps(out, ensure_ascii=False)+"\n")
                    wrote += 1
                    total_out += 1
            if wrote>0:
                out_files.append(str(outp.relative_to(ROOT)))

    # 审计：append summary
    with open(AUD, "a") as f:
        f.write(json.dumps({
            "event":"delayed_reward_append",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": job_id,
            "meta":{"written_files": out_files, "in": total_in, "out": total_out},
            "explain":[f"generated delayed_reward for {len(out_files)} files"]
        })+"\n")

    # 更新回放任务状态（就地覆盖 evidence）
    job["status"]="done"
    job["finished_ts"]=int(time.time()*1000)
    json.dump(job, open(jobp,"w"), ensure_ascii=False, indent=2)

    # 审计：done
    with open(AUD, "a") as f:
        f.write(json.dumps({
            "event":"replay_job_done",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": job_id,
            "meta":{"dt": dt, "symbols": symbols, "out_files": out_files},
            "explain":[f"done replay; updated {str(jobp)}"]
        })+"\n")

    print(f"REPLAY_DONE in={total_in} out={total_out} files={len(out_files)}")
if __name__ == "__main__":
    main()
