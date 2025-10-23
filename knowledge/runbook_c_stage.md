# C 阶段回放/质量闭环要点
- 每小时生成 manifest 与 dataset_manifest，并校验 sha256 与行数。
- 回放一致性：replay_consistency -> ok=true 才能进入质量卡判决。
- 漂移检测：两小时窗口检查特征分布，触发 drift_alert 时执行限制。
