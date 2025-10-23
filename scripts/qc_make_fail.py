#!/usr/bin/env python3
import json, pathlib, time, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
EVID_QC=ROOT/"evidence"/"quality_card"
dt=time.strftime("%Y%m%d", time.localtime())
EVID_QC.mkdir(parents=True, exist_ok=True)
qc={"date":dt,"verdict":"fail","decision":"rollback","reasons":["demo"],"criteria":{"need_accepts_min":999,"expected_pnl_avg_min":0.0}}
json.dump(qc, open(EVID_QC/f"{dt}_quality_card.json","w"), ensure_ascii=False, indent=2)
print("QC_FAIL_WRITTEN")
