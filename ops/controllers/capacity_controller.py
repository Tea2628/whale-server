#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, time, json, pathlib, hashlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audit" / "audit.jsonl"
METRICS = ROOT / "dashboards" / "metrics.json"
FREEZE = ROOT / "ops" / "freeze_window.on"
pathlib.Path(AUDIT.parent).mkdir(parents=True, exist_ok=True)
pathlib.Path(METRICS.parent).mkdir(parents=True, exist_ok=True)

def write_audit(event, meta):
    rec = {"ts": int(time.time()), "event": event, "actor": "system",
           "ref": hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest()[:16],
           "meta": meta}
    with open(AUDIT, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def load_json(p, d):
    try:
        with open(p) as f: return json.load(f)
    except: return d

def save_json(p, o):
    with open(p, "w") as f: json.dump(o, f, ensure_ascii=False, indent=2)

def frozen() -> bool:
    # 允许自愈：设置 OPS_SELF_HEAL=1 可绕过
    return FREEZE.exists() and os.environ.get("OPS_SELF_HEAL","0") != "1"

# --- metrics collection with robust fallbacks ---
def get_cpu_percent():
    try:
        import psutil
        # 某些环境 psutil 安装不完整时会缺属性，做保护
        fn = getattr(psutil, "cpu_percent", None)
        if callable(fn):
            return float(fn(interval=0.3))
    except Exception:
        pass
    # /proc/stat fallback (两次采样)
    def read_stat():
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("cpu "):
                    parts = [float(x) for x in line.split()[1:]]
                    idle = parts[3] + parts[4] if len(parts) > 4 else parts[3]
                    total = sum(parts)
                    return idle, total
        return 0.0, 1.0
    idle1, total1 = read_stat(); time.sleep(0.2)
    idle2, total2 = read_stat()
    dt = max(total2 - total1, 1.0)
    didle = max(idle2 - idle1, 0.0)
    usage = 100.0 * (1.0 - didle / dt)
    return round(usage, 2)

def get_mem_percent():
    try:
        import psutil
        vm = getattr(psutil, "virtual_memory", None)
        if callable(vm):
            return float(vm().percent)
    except Exception:
        pass
    # /proc/meminfo fallback
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            info[k.strip()] = float(v.strip().split()[0])  # KB
    total = info.get("MemTotal", 1.0)
    avail = info.get("MemAvailable", max(info.get("MemFree", 0.0), 0.0))
    used = max(total - avail, 0.0)
    return round(used * 100.0 / max(total, 1.0), 2)

def get_load1():
    try:
        return float(os.getloadavg()[0])
    except Exception:
        return 0.0

def main():
    if frozen():
        write_audit("ops_change", {"decision":"reject","reasons":["freeze_window"],"component":"capacity"})
        return  # 静默退出（停机状态）
    cpu = get_cpu_percent()
    mem = get_mem_percent()
    load1 = get_load1()

    m = load_json(METRICS, {})
    m.setdefault("ts", int(time.time()))
    m["capacity_scale_events_total"] = int(m.get("capacity_scale_events_total", 0))
    m["service_uptime_ratio_7d"] = float(m.get("service_uptime_ratio_7d", 0.999))
    m["queue_backlog_total"] = int(m.get("queue_backlog_total", 0))
    # 轻度策略示例：极端情况下才计一次扩容事件
    if cpu > 90.0 and mem > 90.0 and load1 > 2.0:
        m["capacity_scale_events_total"] += 1
        write_audit("capacity", {"cpu_pct": cpu, "mem_pct": mem, "load1": load1, "action": "scale_hint"})
    else:
        write_audit("capacity", {"cpu_pct": cpu, "mem_pct": mem, "load1": load1, "action": "noop"})
    save_json(METRICS, m)

if __name__ == "__main__":
    main()
