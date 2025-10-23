#!/usr/bin/env python3
import json, time, pathlib, uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVID = ROOT/"evidence"/"replay_job"
AUD  = ROOT/"audit"/"audit.jsonl"

def today():
    return time.strftime("%Y%m%d", time.localtime())

def main():
    dt = today()
    job = {
        "job_id": f"rj_{uuid.uuid4().hex[:8]}",
        "dt": dt,
        "symbols": ["BTCUSDT"],
        "source_manifest": f"manifest/dt={dt}/manifest.json",
        "created_ts": int(time.time()*1000),
        "status": "enqueued"
    }
    EVID.mkdir(parents=True, exist_ok=True)
    outp = EVID/f"{dt}_replay_job.json"
    json.dump(job, open(outp,"w"), ensure_ascii=False, indent=2)

    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD,"a") as f:
        f.write(json.dumps({
            "event":"replay_job_enqueue",
            "ts": int(time.time()*1000),
            "actor":"service",
            "ref": job["job_id"],
            "meta":{"dt": dt, "symbols": job["symbols"]},
            "explain":[f"enqueue -> {str(outp)}"]
        }, ensure_ascii=False) + "\n")

    print(f"ENQUEUED -> {outp} job_id={job['job_id']}")
if __name__ == "__main__":
    main()
