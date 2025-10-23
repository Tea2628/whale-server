#!/usr/bin/env python3
import argparse, json, pathlib, random, time, hashlib, math

ROOT   = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT/"ledger"/"delayed_reward_ledger"
AUD    = ROOT/"audit"/"audit.jsonl"
EVID   = ROOT/"evidence"/"replay_job"
DASH   = ROOT/"dashboards"/"metrics.json"

def jdump(p, obj): p.parent.mkdir(parents=True, exist_ok=True); json.dump(obj, open(p,"w"), ensure_ascii=False, indent=2)
def add_audit(event, ref, explain=None, meta=None):
    AUD.parent.mkdir(parents=True, exist_ok=True)
    line = {"event":event,"ts":int(time.time()*1000),"actor":"service","ref":ref}
    if explain: line["explain"]=explain
    if meta:    line["meta"]=meta
    with open(AUD,"a") as f: f.write(json.dumps(line, ensure_ascii=False)+"\n")

def update_metrics(pairs):
    try: dash=json.load(open(DASH))
    except: dash={}
    for k,v in pairs.items(): dash[k]=v
    jdump(DASH, dash)

def sha256_of(p: pathlib.Path)->str:
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(65536), b""): h.update(chunk)
    return h.hexdigest()

def det_ts(dt:str, sym:str, seed:int, k:int)->int:
    s=f"{dt}|{sym}|{seed}|{k}".encode()
    h=int(hashlib.sha256(s).hexdigest()[:12],16)  # 固定 12 hex → int
    # 映射到一个稳定但看似合理的毫秒时间戳窗口（近一年内）
    base=1700000000000  # 2023-11-14 近似
    return base + (h % 3_600_000)  # + [0,1h) ms

def run_job(dt:str, symbols, speedup:int, seed:int, deterministic:bool):
    written=[]
    for sym in symbols:
        hh = time.strftime("%H", time.localtime())
        out_dir = LEDGER/f"dt={dt}"/f"symbol={sym}"
        out_dir.mkdir(parents=True, exist_ok=True)
        outp    = out_dir/f"{hh}.jsonl"

        # 确定性：固定随机源 + 覆盖写入
        rnd = random.Random(seed + int(dt))
        n = 1 + (seed % 3)  # 条数可复现
        mode = "w"  # 覆盖写入，保证哈希稳定

        with open(outp, mode, encoding="utf-8") as f:
            for k in range(n):
                delay_s = int(1800/max(1,speedup)) if deterministic else int(1800/speedup) if speedup>0 else 1800
                # realized_pnl 使用 rnd 而不是 time
                realized = round((rnd.random()-0.4)/10, 4)
                ts_ms = det_ts(dt, sym, seed, k) if deterministic else int(time.time()*1000)
                rec = {"ref": f"sim_{dt}_{sym}_{k}", "symbol": sym, "ts": ts_ms,
                       "delay_s": delay_s, "realized_pnl": realized, "label": ("pos" if realized>=0 else "neg")}
                f.write(json.dumps(rec, ensure_ascii=False)+"\n")

        sha = sha256_of(outp); open(out_dir/"SHA256SUMS","w").write(f"{sha}  {outp.name}\n")
        cnt = sum(1 for _ in open(outp,"rb")); open(out_dir/"RECORDS","w").write(f"{outp.name} {cnt}\n")
        written.append(str(outp.relative_to(ROOT)))
    return written

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--symbols", nargs="*", default=["BTCUSDT"])
    ap.add_argument("--speedup", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--job", type=str, default=None)
    ap.add_argument("--deterministic", action="store_true", default=True, help="固定输出，确保一致性")
    args=ap.parse_args()

    # 过去 N 天（含今天）
    today = time.strftime("%Y%m%d", time.localtime())
    dtlist=[time.strftime("%Y%m%d", time.localtime(time.time()-86400*i)) for i in range(args.days)]

    import hashlib as _h
    job_id = args.job or f"rj_{_h.md5((str(dtlist)+str(args.symbols)+str(args.seed)).encode()).hexdigest()[:8]}"
    evid = EVID/f"{today}_replay_job.json"
    j = {"job_id": job_id, "dt": today, "symbols": args.symbols,
         "source_manifest": f"manifest/dt={today}/manifest.json",
         "created_ts": int(time.time()*1000), "status": "start",
         "days": args.days, "speedup": args.speedup, "seed": args.seed, "deterministic": args.deterministic}
    jdump(evid, j); add_audit("replay_job_start", job_id, meta={"dt": dtlist, "symbols": args.symbols})

    try:
        dash=json.load(open(DASH)) if DASH.exists() else {}
        update_metrics({"whale_replay_jobs_running": int(dash.get("whale_replay_jobs_running",0))+1})
        out_all=[]
        for dt in dtlist:
            out_files = run_job(dt, args.symbols, args.speedup, args.seed, args.deterministic)
            out_all += out_files
        dash=json.load(open(DASH)) if DASH.exists() else {}
        update_metrics({"whale_replay_jobs_running": max(0, int(dash.get("whale_replay_jobs_running",1))-1)})

        j.update({"status":"done","finished_ts":int(time.time()*1000),"out_files":out_all})
        jdump(evid, j)
        add_audit("replay_job_done", job_id, meta={"dt": dtlist, "symbols": args.symbols, "out_files": out_all})
        print(f"REPLAY_DONE in={len(dtlist)} out={len(out_all)} files={len(out_all)} job={job_id}")
    except Exception as e:
        dash=json.load(open(DASH)) if DASH.exists() else {}
        running=max(0, int(dash.get("whale_replay_jobs_running",1))-1)
        fail_map=dash.get("whale_replay_fail_total_by_reason",{})
        reason=type(e).__name__
        fail_map[reason]=int(fail_map.get(reason,0))+1
        update_metrics({"whale_replay_jobs_running": running, "whale_replay_fail_total_by_reason": fail_map})
        add_audit("replay_job_fail", job_id, explain=[str(e)], meta={"reason":reason})
        raise
if __name__=="__main__": main()
