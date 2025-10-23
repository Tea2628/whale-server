#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retention & manifest updater (hot/warm tiers)
- <=30 天：更新 manifest/dataset_manifest.jsonl（含 sha256）
-  >30 天：删除文件；统计删除失败计数并写入审计
"""
import os, time, json, hashlib, pathlib, sys

BASES = ["release", "ledger", "manifest", "evidence", "dashboards"]  # 可按需扩展
DAYS_WARM = 30
AUDIT = "audit/audit.jsonl"
MANIFEST = "manifest/dataset_manifest.jsonl"

def sha256sum(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def audit(event, meta):
    rec = {
        "ts": int(time.time()),
        "event": event,
        "actor": "system",
        "ref": meta.get("ref", ""),
        "decision": meta.get("decision", ""),
        "reasons": meta.get("reasons", []),
        "slo_check": {"pass": True}
    }
    pathlib.Path(os.path.dirname(AUDIT)).mkdir(parents=True, exist_ok=True)
    with open(AUDIT, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

now = time.time()
deleted = 0
errors = 0
wrote = 0

pathlib.Path("manifest").mkdir(exist_ok=True)
mf = open(MANIFEST, "a")

for base in BASES:
    if not os.path.isdir(base):
        continue
    for root, _, files in os.walk(base):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                # 文件可能刚被移动/删除
                continue
            age_days = (now - st.st_mtime) / 86400.0

            if age_days <= DAYS_WARM:
                # 写/追加 manifest 记录
                try:
                    mf.write(json.dumps({"path": p, "sha256": sha256sum(p), "ts": int(now)}) + "\n")
                    wrote += 1
                except Exception:
                    errors += 1
            else:
                # >30 天：删除（可改为移动到 cold/）
                try:
                    os.remove(p)
                    deleted += 1
                except Exception:
                    errors += 1

mf.close()

audit("retention", {
    "decision": "done",
    "reasons": [f"wrote={wrote}", f"deleted={deleted}", f"errors={errors}"]
})

print(f"[retention] wrote={wrote} deleted={deleted} errors={errors} -> {MANIFEST}")
