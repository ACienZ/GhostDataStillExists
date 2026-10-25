# Ghost Data Still Exists — 设计、任务拆分与验收标准

- 状态：v0.1（初始设计，随实现更新）
- 日期：2026-10-25
- 作者：DSH Team（Lead + teammates）
- 上游：`docs/refs/hackerrank-orchestrate-october26-main/{AGENTS.md,README.md,problem_statement.md,dataset/}`

## 1. 问题理解（可检查的合同）

对 `dataset/deletion_requests.csv` 中 518 个 case，输出 `case_id,deletion_status,steps_json`：

- `deletion_status ∈ {COMPLETE, INCOMPLETE, NOT_APPLICABLE}`；
- `steps_json` 为有序数组，每项 7 个字段：`step_no, phase, system_id, resource_id, operation, state, evidence_id`；
- `NOT_APPLICABLE` → `[]`（未授权删除：访问/更正/导出/退订等）；
- 对授权删除：先用证据重建 `audit_at` 时刻的资源状态，再按 `deletion_rules.csv` 决定每个数据类别的处置（DELETE/REDACT/ANONYMIZE/RETAIN），判断 COMPLETE 与否，并给出 remediation + verification；
- 排序：phase 顺序 FINDING→REMEDIATION→VERIFICATION；同 phase 内先按操作表顺序，再按 `system_id`、`resource_id` 升序；
- 证据引用：FINDING 必须引用 `file_id`/`activity_id`/`audit_id`；INCOMPLETE 的 REMEDIATION 与后续 VERIFICATION 用空字符串；COMPLETE 的 VERIFICATION 必须引用证明当前状态的证据；不得引用组织方真值或晚于 `audit_at` 的证据。

判定 "完整删除" 的充要条件（problem_statement）：
1. 每个相关副本都得到 `deletion_rules.csv` 要求的处置；
2. 没有活跃的 sync/import/restore 路径能重建数据；
3. 必须保留的记录仍只含允许的标识符；
4. 必须保留的记录仍可用。

## 2. 数据集事实（已核实的观察）

| 文件 | 规模/结构 |
| --- | --- |
| `deletion_requests.csv` | 518 行（case_33 … case_550）；`reported_status` 分布 COMPLETE 254 / PARTIALLY_COMPLETE 152 / NOT_STARTED 112 |
| `sample_deletion_requests.csv` / `sample_output.csv` | 32 行官方样例（case_01–case_32），含完整 steps |
| `user_identities.csv` | 850 个 user；字段 user_id/name/email/phone/email_hash/updated_at |
| `user_audit_log.csv` | 307 条历史身份变更（email 107 / email_hash 107 / phone 92） |
| `system_activity.csv` | 4012 条全局活动；事件类型 DELETE/UPDATE/SYNC/INDEX/SEND_EMAIL/REFRESH_CACHE/RETAIN/ANONYMIZE/REDACT/CREATE_EXPORT/CHECK_DATA_FLOW/DISABLE_DATA_FLOW/BLOCK_RESTORE/CHECK_RESTORE_ACCESS/LINK_RESOURCE_IDENTITY/CLASSIFY_REQUEST/RESTORE_BACKUP |
| `deletion_rules.csv` | 15 条 category→action 规则（见 §3） |
| `evidence_files.csv` | 94 个证据文件（28 json / 26 log / 24 sql / 4 pdf / 11 png / 1 txt） |
| `evidence/` | 时间跨度 2026-01-29 … 2026-10-01；95 个文件 |

关键结构发现：

1. **case → user 唯一可解**：用 `user_identities` + `user_audit_log`（历史 email）可把 518 个请求 email 全部唯一解析到 user_id；样例 32 个也全部唯一。
2. **wave 结构**：hidden case 主要是"每 10 个 case 一个 wave"，同一 wave 的 `audit_at` 同一天；每个 wave 恰有 **1 个 wave 证据文件**（捕获时间在 audit 当天/前一天，覆盖该 wave ≥3/4 的 case 用户）。使用该文件即可重建 wave 内 10 个 case 的场景。
3. **special case**：case_33–case_72、case_533–case_550 等零散日期 case，是手工构造的边界案例，各自有专用证据文件（图片/PDF/小型 SQL/JSON/log），样例 case_01–case_32 也是这类。
4. **非删除案例**：`system_activity.event_type=CLASSIFY_REQUEST` 恰好 10 条，且 518 个请求文本中恰好 10 个是访问/更正/导出/退订/保持类请求（case_533–case_542），预期 `NOT_APPLICABLE`。
5. **证据格式族**（需要统一解析为 Observation）：
   - `record_lookup` 日志行：`system / resource_id / record_type / result / subject_reference`；
   - readback trace：查询 start/completed 成对出现，completed 行含完整字段（rows/http_status/profile/connector/backup/support/analytics/audit）；
   - `service_resource_export_*.json`：按 service 分组的 profile_lookups / profiles / restore_entries / exports / connectors / index_queries / audit_records / tickets；
   - `customer_data_inventory_*.sql`、`customer_data_*_replica_*.sql`：SQLite DDL + INSERT 表；
   - `customer_data_snapshot_bundle_*.json`：按 data_store/collection 分组的 snapshots；
   - `connector_configurations_*.json` / `customer_export_manifest_*.json` / `security_audit_ledger_*.json`：records[]（record_type/result/subject_reference）；
   - `customer_account_handover_*.txt`：`时间 | system | resource_id | record_type | state | subject`；
   - PDF：pypdf 可提取文本（账户历史、法律保留登记、安全保留摘录、投递更正附件）；
   - PNG：需 OCR（macOS Vision），输出为控制台/工单/保留视图文本。
6. **证据冲突与时效**：同一 resource 可有多条不同时间的记录（如 `account_8473` 先 FOUND 后 NOT_FOUND），以 `audit_at` 前最近一次为准；副本（failover/read/regional/reporting replica）可能滞后，需要按"主库 vs 副本"漂移解释。
7. **匿名记录归属**：被 ANONYMIZE 的 analytics profile 会丢失全部直接标识符；归属需要靠 (a) 快照 bundle 中按 user 排序的位置关系、(b) `system_activity` 中该 case 工作流的时间窗、或 (c) 消除法推断。该类资源数量很少，属于已知不确定点（见 §8）。
8. **样例证据选择规律**（从 32 个样例反推）：每个 step 引用"能证明该资源在 `audit_at` 状态、且 `captured_at <= audit_at` 的证据文件"；通常是一个覆盖该 case 的 wave/专用证据包。INCOMPLETE 的 remediation/未来 verification 一律空 evidence。

## 3. 策略与处置规则（来自 deletion_rules.csv）

| rule | category | condition | action | 本系统的判定 |
| --- | --- | --- | --- | --- |
| 01 | USER_PROFILE | Always | DELETE | 记录存在 → REPORT_REMAINING_RECORD + DELETE_RECORD |
| 02 | SECONDARY_IDENTIFIER | Always | DELETE | 资源存在 → DELETE |
| 03 | SEARCH_INDEX_ENTRY | Always | DELETE | FOUND → DELETE |
| 04 | CACHE_ENTRY | Always | DELETE | 存在 → DELETE |
| 05 | SUPPORT_MESSAGE | 含共享上下文 | REDACT | IDENTIFIABLE → REPORT_EXPOSED_PII + REDACT |
| 06 | SUPPORT_ATTACHMENT | 只属于主体 | DELETE | FOUND → DELETE |
| 07 | ANALYTICS_PROFILE | 仍可归属 | ANONYMIZE | IDENTIFIABLE → REPORT_EXPOSED_PII + ANONYMIZE |
| 08 | PRODUCT_TELEMETRY | 仍可归属 | ANONYMIZE | 同 07 |
| 09 | USER_EXPORT | Always | DELETE | FOUND → DELETE |
| 10 | MARKETING_PROFILE | Always | DELETE | FOUND → DELETE |
| 11 | EMAIL_DELIVERY_LOG | 含邮箱 | REDACT | 含 email → REDACT |
| 12 | SECURITY_AUDIT_LOG | 保留期内 | RETAIN | FOUND → VERIFY_RECORD_PRESENT |
| 13 | LEGAL_HOLD_RECORD | 法律保留有效 | RETAIN | FOUND → VERIFY_RECORD_PRESENT |
| 14 | BACKUP_ARCHIVE | 可阻断恢复 | RETAIN | restore_allowed → REPORT_RESTORE_RISK + BLOCK_RESTORE；不可恢复 → VERIFY_RESTORE_BLOCKED |
| 15 | ACCOUNT_TOMBSTONE | 已删除且只需稳定 user_id | REDACT | 含直接标识符 → REPORT_EXPOSED_PII + REDACT；已清除 → VERIFY_RECORD_REDACTED |

未在规则表出现但可能出现在证据/活动中的类别（SECURITY_AUDIT_LOG 之外的 RETAIN 类、LEGAL_HOLD）按"必须保留 + verify present"处理。

## 4. 从样例归纳的 steps 生成规则（待实现后用 32 样例回归验证）

对每个 case：

1. **intent**：非删除请求 → `NOT_APPLICABLE` + `[]`。
2. **场景集合**：从 case 的 wave/专用证据包中提取属于该 user 的 Observation（含 account 是否存在、各系统资源、retained 记录、数据流、备份、tombstone）。
3. **status**：若存在任何违反规则当前状态的资源（应删仍存在 / 应 redact-anonymize 仍可识别 / 数据流 active / 备份可恢复）→ `INCOMPLETE`；否则 `COMPLETE`。
4. **FINDING**（仅 INCOMPLETE）：
   - 应 DELETE 且存在 → `REPORT_REMAINING_RECORD`；
   - 应 REDACT/ANONYMIZE 且仍可识别 → `REPORT_EXPOSED_PII`；
   - connector enabled → `REPORT_ACTIVE_DATA_FLOW`；
   - backup restore_allowed → `REPORT_RESTORE_RISK`。
5. **REMEDIATION**（仅 INCOMPLETE）：每个 finding 对应一个操作（DISABLE_DATA_FLOW / BLOCK_RESTORE / DELETE_RECORD / REDACT_RECORD / ANONYMIZE_RECORD），evidence 为空。
6. **VERIFICATION**：覆盖"场景中每个资源的目标状态" + 基线 `account_service.account_<id>` 的 `VERIFY_RECORD_ABSENT`；retained → `VERIFY_RECORD_PRESENT`；COMPLETE 时引用证据，INCOMPLETE 时 evidence 为空。
7. **排序**：phase 表顺序 → operation 表顺序 → system_id → resource_id。
8. **evidence 选择**：优先"显式观察到该资源状态"的证据包；否则如 wave 证据包是该 case 的审计包且能证明状态（如账号不在快照表中）也可引用。若同资源多个候选，取 `captured_at` 最大且 `<= audit_at` 者（样例验证）。

## 5. 系统架构（Python，确定性优先）

```text
src/ghost_audit/
  __init__.py
  config.py            # 路径、模型配置（密钥只从 env / 本地未提交文件读取）
  dataset.py           # 读取 6 个 CSV + evidence manifest；数据集完整性检查
  identity.py          # current + historical identifiers；case→user；token→user
  intent.py            # 删除意图分类（多语言规则 + 可选 LLM 复核/缓存）
  evidence/
    __init__.py
    base.py            # Observation dataclass / 枚举 / 归一化
    sql_dump.py        # SQL 快照 → Observations
    json_docs.py       # bundle / service export / records[] JSON
    logs.py            # record_lookup / readback / 半结构化 log
    handover.py        # handover txt
    documents.py       # PDF 文本 + PNG OCR（macOS Vision）
    registry.py        # 按文件类型路由 + 证据索引
  activity.py          # system_activity 索引：case 工作流时间窗、LINK/CLASSIFY、
                       # 资源→case 候选
  scenario.py          # case→wave 证据包；Observation 归属；状态时间线重建
  policy.py            # category→action、finding→remediation 映射
  planner.py           # status + steps 生成 + 排序 + evidence 选取
  output.py            # output.csv 写出（严格 JSON、排序、契约自检）
  llm.py               # DeepSeek client（仅 intent 复核等窄用途；记录 usage）
  cli.py               # `python -m ghost_audit run --dataset ... --output ...`
evaluation/
  evaluate.py          # 样例回归 + 契约 + 指标（case/step/field/sequence/evidence）
  cases/               # 自建独立评估案例（数据 + 独立手写期望）
  evaluation_report.md
  usage_report.md
tests/                 # pytest：合同、身份、策略、转换、变异、样例回归
scripts/               # build_code_zip.py / validate_submission.py / ocr_images.swift
submission/            # output.csv / code.zip / log.txt / INTERVIEW_GUIDE.md
```

设计原则：证据解析、身份解析、状态重建、策略应用全部确定性；模型只用于窄语义判断（意图复核、冲突解释），且必须可缓存、可复现、可计量。

## 6. 任务拆分与验收标准

| # | 任务 | 负责人 | 验收 |
| --- | --- | --- | --- |
| 1 | 仓库/文档/GitHub issue+Project/branch 脚手架 | Lead | issues 与 Project 条目存在；docs 可读 |
| 2 | 证据解析层（§5 evidence/*, activity.py） | evidence-parser | 95 个证据文件可解析；pytest 覆盖格式；无静默跳过 |
| 3 | 身份解析 + intent 分类 | Lead | 518 case 全部唯一解析；10 个非删除意图识别正确 |
| 4 | 场景重建 + policy + planner + CLI | Lead | 32 样例 status 100%、steps 结构/顺序/字段匹配；输出契约通过 |
| 5 | 独立评估案例（≥10，含指定边界）+ 变换测试 + 变异测试 + 契约校验 | eval-harness | 每个案例有独立手写期望与理由；故意 bug 能被测试发现 |
| 6 | 全量 518 运行 + output.csv | Lead | 518 行、排序、契约、证据有效性自检 |
| 7 | 评估/用量报告、README、INTERVIEW_GUIDE、code.zip、submission 打包 | docs-packaging | 从干净目录解压可复现；实测 token/费用 |
| 8 | GitHub PR/CI/merge、最终审计 | Lead | CI 绿；PR 已审阅合并；远端状态与本地一致 |

## 7. 评估计划

1. **官方样例回归**（开发回归集，仅用于调试，不宣称泛化）：32 个样例，报告 status 匹配率、step 集合 F1、字段级匹配率、sequence 匹配率、evidence 匹配率。
2. **独立额外案例**：在 `evaluation/cases/` 构造 mini dataset（CSV + evidence 文件 + 手写 expected JSON，独立于实现逻辑），覆盖：历史身份遗漏、副本残留、删除后重新同步、恢复风险、必须保留记录、允许保留的墓碑、未授权删除、数据流仍活跃、支持消息共享上下文、导出残留等。
3. **输入变换**：打乱行序、加入诱饵记录、仅修改 `reported_status` → 结果集合必须不变（status 除真实证据外不随 claim 变化）。
4. **测试有效性**：变异测试——故意注入典型错误（忽略历史邮箱、盲信 reported_status、忽略 sync 重建风险、错误排序），断言评估器能报错。
5. **输出契约**：行数/排序/列/JSON/enum/step_no 连续/phase 顺序/operation 顺序/evidence 引用规则/交叉一致性。

## 8. 风险、未核实事项、已确认决定

| 项 | 状态 | 说明 |
| --- | --- | --- |
| hidden canonical 精确内容 | 未核实 | 只有 32 个样例有标注；wave case 逻辑靠规则反推 + 契约约束，无法直接测准确率 |
| 匿名 analytics 的 user 归属 | 未核实 | 用 snapshot bundle 排序 + activity 时间窗 + 消除法近似；可能少量资源 id 不同 |
| 评分权重细节 | 未核实 | 排行榜/题面只说明维度，不臆测权重；以合同正确性为第一目标 |
| LLM 在本任务中的用途 | 已决定 | 仅做多语言意图复核（temperature=0，响应缓存，记录 usage）；事实/状态/顺序全确定性 |
| 晚于 audit_at 的证据 | 已决定 | 仅用于静态资源归属旁证（身份链接），不改变 audit_at 状态结论；在报告中披露 |
| 图片 OCR | 已决定 | 本机 macOS Vision OCR；Linux CI 缺 OCR 时相关测试 skip，代码中保留清晰报错 |
| 官方 deadline | 未核实 | 参考仓库明确说未配置，不虚构 |

## 9. 成本与运行

- 全量运行：518 case + 94 evidence 文件，纯 Python 确定性解析 + 1 次/案 intent LLM 调用（可缓存）。实测 token/费用写入 `evaluation/usage_report.md`。
- 无 API key 时必须能运行：LLM 关闭时使用确定性意图分类，输出仍完整（报告中说明）。
