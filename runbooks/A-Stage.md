# A-Stage Runbook (最小可运行集)
**目标**：校验契约 → 门禁决策 → 投递(file/telegram-stub) → 审计 → 观测KPI  
**目录结构**：schemas/、samples/、scripts/、signals/YYYYMMDD、dead_letter、audit/audit.jsonl、release/YYYYMMDD、logs/

## 常用命令
- 激活环境：`. .venv/bin/activate`
- 校验样例：`./scripts/validate_contracts.py`
- 规则仿真（单个）：`python3 scripts/rules_min.py samples/features/valid/one.json > /tmp/sim.json`
- 投递信号（单个）：`./scripts/emit_signal.sh /tmp/sim.json && python3 scripts/deliver.py /tmp/sim.json`
- 批量仿真：`./scripts/simulate_batch.sh`
- 批量投递（今日）：`./scripts/deliver_today.sh`
- KPI 摘要：`python3 scripts/metrics_kpi.py`

## 开关
- `config/gate.yml`
  - `deliver.file.enabled: true|false`
  - `deliver.telegram.enabled: true|false`（A 阶段为 stub，仅写 logs/telegram.log 与审计）

## 验收要点（A 阶段）
- 三分支：ACCEPT → `signals/YYYYMMDD/*.json`、ABSTAIN → 审计、REJECT → `dead_letter/*.json`
- 审计：`audit/audit.jsonl` 持续追加 gate/deliver 事件
- 观测：`dashboards/metrics.json` 输出 5 件 KPI（占位）

## 回滚（最小）
- 清理当日产物（不删代码）：`rm -rf signals/$(date +%Y%m%d) release/$(date +%Y%m%d) logs/telegram.log`
- 清理所有运行期产物（保留样例/脚本）：`rm -rf signals dead_letter audit release logs dashboards && mkdir -p audit signals dead_letter`

