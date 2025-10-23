# D-Stage｜合规与安全基线（最小可行集）
- 角色：ingest, features, rules, gpt, gate, deliver, replay, ops（最小权限）  
- GPT 主脑权限：仅“建议写入 + 审计写入”，无外部下单/读密钥  
- 机器身份：各服务独立 Token，不共用  
- 数据分级：P0/P1/P2/P3；P0 不落盘；审计≥180天 [oai_citation:4‡开发总清单.txt](file-service://file-4CgcdamFSbNvsX7WLtpvim)  
- 传输与落盘：TLS 强制；P1/P2 卷级或字段级加密，sha256 校验 [oai_citation:5‡开发总清单.txt](file-service://file-4CgcdamFSbNvsX7WLtpvim)  
- 访问边界：管理端口非公网 + 白名单 [oai_citation:6‡开发总清单.txt](file-service://file-4CgcdamFSbNvsX7WLtpvim)
