#!/usr/bin/env python3
import pathlib, time, json, argparse, shutil, datetime as dt

ROOT   = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT/"ledger"
AUD    = ROOT/"audit"/"audit.jsonl"

def parse_dt(dirname: str):
    # 期望形如 dt=20251023
    if not dirname.startswith("dt="): return None
    try:
        return dt.datetime.strptime(dirname[3:], "%Y%m%d").date()
    except Exception:
        return None

def older_than(days: int, d: dt.date) -> bool:
    return (dt.date.today() - d).days > days

def collect_targets(retain_days: int):
    # 需要检查的一级目录：market_tick/features/signals/gate/policy_change
    bases = [LEDGER/x for x in ["market_tick","features","signals","gate","policy_change"]]
    targets = []
    for base in bases:
        if not base.exists(): continue
        for d in base.iterdir():
            if not d.is_dir(): continue
            # 结构为 base/dt=YYYYMMDD/(symbol=...)?/HH.jsonl
            d_dt = parse_dt(d.name)
            if not d_dt: continue
            if older_than(retain_days, d_dt):
                targets.append(d)
    return targets

def write_audit(event, explain):
    AUD.parent.mkdir(parents=True, exist_ok=True)
    with open(AUD,"a",encoding="utf-8") as f:
        f.write(json.dumps({
            "event": event,
            "ts": int(time.time()*1000),
            "actor": "service",
            "ref": time.strftime("%Y%m%d", time.localtime()),
            "explain": explain
        }, ensure_ascii=False) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30, help="retention days")
    ap.add_argument("--dry-run", action="store_true", help="show only, do not delete")
    args = ap.parse_args()

    tgs = collect_targets(args.days)
    if args.dry_run:
        print(f"RETENTION DRY-RUN days={args.days} will remove {len(tgs)} dt partitions:")
        for d in tgs: print("  -", d.relative_to(ROOT))
        write_audit("ledger_retention", [f"dry_run days={args.days}", f"targets={len(tgs)}"])
        return

    removed = []
    for d in tgs:
        try:
            shutil.rmtree(d)
            removed.append(str(d.relative_to(ROOT)))
        except Exception as e:
            print(f"[WARN] failed to remove {d}: {e}")

    print(f"RETENTION APPLIED days={args.days} removed={len(removed)}")
    write_audit("ledger_retention", [f"applied days={args.days}", f"removed={len(removed)}"])
    if removed:
        # 顺带提示可手动重新生成当天 manifest（历史被清理不影响当天）
        print("NOTE: old partitions pruned. Today's manifest remains valid.")
if __name__ == "__main__":
    main()
