#!/usr/bin/env python3
import json, pathlib, time, hashlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
LEDGER=ROOT/"ledger"/"delayed_reward_ledger"
AUD =ROOT/"audit"/"audit.jsonl"
DASH=ROOT/"dashboards"/"metrics.json"

def sha256(p: pathlib.Path)->str:
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(65536), b""): h.update(chunk)
    return h.hexdigest()

def run_once(seed:int):
    dt=time.strftime("%Y%m%d", time.localtime()); sym="BTCUSDT"
    subprocess.run(["python3","scripts/replay_job_run.py","--days","1","--symbols",sym,"--seed",str(seed),"--deterministic"], check=True)
    hh=time.strftime("%H"); target=LEDGER/f"dt={dt}"/f"symbol={sym}"/f"{hh}.jsonl"
    return sha256(target)

def main():
    hashes=[run_once(123) for _ in range(5)]
    ok = all(h==hashes[0] for h in hashes)
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD,"a") as f:
        f.write(json.dumps({"event":"replay_consistency","ts":int(time.time()*1000),"actor":"service","ref":time.strftime("%Y%m%d"),"meta":{"runs":5,"hashes":hashes,"ok":ok}}, ensure_ascii=False)+"\n")
    try: dash=json.load(open(DASH))
    except: dash={}
    dash["whale_replay_consistency_ok"]=bool(ok)
    json.dump(dash, open(DASH,"w"), ensure_ascii=False, indent=2)
    print(f"CONSISTENCY {'OK' if ok else 'FAIL'} runs=5")
if __name__=="__main__": main()
