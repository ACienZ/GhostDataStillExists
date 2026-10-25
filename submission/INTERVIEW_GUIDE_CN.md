# INTERVIEW_GUIDE_CN — Ghost Data Still Exists（中文版）

> **状态：定稿 — 所有数字与提交产物一致。**
> 本文件是 [`INTERVIEW_GUIDE.md`](INTERVIEW_GUIDE.md) 的中文翻译，供中文面试/评审
> 使用；英文版为基准，两版内容与实测数字完全一致。
> 本指南面向现场面试：说明系统做什么、如何决策、如何评估、还有哪些不确定之处。
> 下文每个实测数字都来自**最终全量运行**
> （2026-10-25T03:51Z，命令
> `uv run python -m ghost_audit run --dataset <DATASET_DIR> --output output.csv --llm-intent`），
> 并与 `evaluation/evaluation_report.md`、`evaluation/usage_report.md` 一致。
> 本文件没有任何估算或编造的数字。
>
> **面试中要明确说清楚的核心点：**审计是**确定性的**——证据解析、身份解析、
> 时点重建、策略、修复/验证规划与排序全部基于规则；模型只是对 10 个低信号
> 意图案例的**顾问性交叉复核**，永远不会覆盖确定性结论。32 个公开样例指标是
> **开发回归集**，不是隐藏集准确率。

## 1. 一段话概述

Northstar Shop 的删除工作流可能报告 *Complete*，但客户的个人数据仍然残留在
次级数据库、副本、支持附件、搜索索引、分析记录、导出文件、日志、归档或备份中；
而且活跃的同步/恢复链路可能在删除之后重新制造数据。我们的 agent 对全部 518 条
删除请求做审计：解析面向参与者的证据，关联用户的**当前与历史**标识符，重建每个
案例 `audit_at` 时刻的资源状态，套用 `deletion_rules.csv`，并输出带证据引用的、
有序的 `FINDING → REMEDIATION → VERIFICATION` 处置计划。审计本身是确定性的；
模型是可选的、带缓存的顾问性意图复核层（最终运行 10 次调用），确定性分类器
始终拥有最终决定权。

## 2. 问题理解（我们实现的契约）

- 每个案例的输入：`case_id,email,requested_at,reported_status,reported_at,audit_at,request_text`。
- 每个案例的输出：`deletion_status`（`COMPLETE` / `INCOMPLETE` / `NOT_APPLICABLE`）
  以及有序的 `steps_json`。
- `reported_status` / 活动中的 `reported_result` 只是**声明**，不是完成证明。
- 只有 `captured_at <= audit_at` 的证据才能用于决定答案；更晚的证据只能用于
  静态身份关联（已在设计文档中披露）。
- `NOT_APPLICABLE` = 请求文本没有授权删除（访问、更正、导出、营销退订等）→ `[]`。
- 只有同时满足以下条件，删除才算完成：每一份相关副本都得到了规则要求的处置；
  不存在能重新制造数据的活跃同步/导入/恢复链路；保留记录中只含允许的标识符；
  应当保留的记录仍然可用。
- 步骤结构：恰好 `step_no, phase, system_id, resource_id, operation, state,
  evidence_id`；三个阶段按顺序；阶段内按操作表顺序、再按 `system_id`、再按
  `resource_id` 升序排列。

## 3. 架构一览

```text
dataset CSVs ──► dataset.py ──► identity.py ──► intent.py (deletion or not)
                                                    │
evidence files ─► evidence/* parsers ─► Observation (system, resource, record_type,
   SQL/JSON/log/PDF/PNG OCR                        state, captured_at, evidence_id)
                                                    │
activity stream ─► activity.py ──► scenario.py (case↔evidence packages,
                                    point-in-time state at audit_at)
                                                    │
deletion_rules.csv ─► policy.py ──► planner.py (status + findings + remediation +
                                    verification + ordering + evidence selection)
                                                    │
                                    output.py (strict CSV/JSON) ──► output.csv
                                              └─ optional llm.py (intent review, cached)
```

设计原则：**确定性优先**。所有事实、状态、策略动作、排序与序列化都由规则化的
Python 完成。可选模型只对歧义的多语言 `request_text` 做意图分类的复核/标记。

| 阶段 | 模块 | 是否确定性 |
| --- | --- | --- |
| 数据集加载 / 完整性检查 | `dataset.py` | 是 |
| 身份解析（当前 + 历史） | `identity.py` | 是 |
| 请求意图分类 | `intent.py`（可选 `llm.py` 复核） | 默认是；LLM 只做复核 |
| 证据解析为观测 | `evidence/*` | 是 |
| 活动流索引 | `activity.py` | 是 |
| 案例↔证据包与状态重建 | `scenario.py` | 是 |
| 策略映射（`deletion_rules.csv`） | `policy.py` | 是 |
| 状态/步骤规划、排序、证据选择 | `planner.py` | 是 |
| CSV/JSON 序列化 | `output.py` | 是（排序固定、无随机性） |
| CLI / 参数 / 缓存 | `cli.py`、`llm.py` | 是（相同输入 + 缓存下） |

最终模块清单（`find src/ghost_audit -name "*.py"` 实际核实）：
`__init__.py`、`__main__.py`、`cli.py`、`config.py`、`dataset.py`、
`identity.py`、`intent.py`、`llm.py`、`ocr.py`、`activity.py`、`scenario.py`、
`policy.py`、`planner.py`、`output.py`，以及 `evidence/` 包
（`base.py`、`documents.py`、`handover.py`、`json_docs.py`、`logs.py`、
`records.py`、`registry.py`、`result.py`、`sql_dump.py`、`_util.py`）。

最终 CLI 参数（`uv run python -m ghost_audit run --help` 实际核实）：
`--dataset`、`--requests`、`--sample`、`--output`、`--skip-images`、
`--no-llm`、`--llm-intent`、`--llm-budget`、`--intent-cache`、
`--emit-blueprint`、`--quiet`。提交所用运行命令使用
`--llm-intent`（默认预算 40；实际使用 10 次调用，因此缓存命中）。

## 4. 证据处理

各证据族如何归一化为状态观测：

| 格式 | 文件数 | 我们提取的内容 |
| --- | --- | --- |
| `record_lookup` 日志 | `.log` | system、resource_id、record_type、观测结果、主体引用 |
| readback 轨迹 | `.log` | 成对的 start/completed 查询；completed 行携带 profile/connector/backup/audit 字段 |
| `service_resource_export_*.json` | `.json` | 分组的 profile/restore/export/connector/index/audit/ticket 记录 |
| 快照包 | `.json` | 按数据存储/集合的快照（包括作为事实的*缺席*） |
| 记录清单 / connector 配置 / 审计台账 | `.json` | 带 record_type/result/subject_reference 的 `records[]` |
| SQL 快照导出 | `.sql` | 主库/区域副本/报表副本/故障转移副本的 SQLite DDL + INSERT |
| 交接 / 控制台文本 | `.txt` | `time \| system \| resource_id \| record_type \| state \| subject` |
| PDF | `.pdf` | 抽取文本（账号历史、法定留存台账、安全留存摘录） |
| 截图 | `.png` | 通过 macOS Vision 做 OCR（`scripts/ocr_images.swift`） |

面试中值得追问的关键决策：

- **声明 vs 证据**：工作流状态与活动 `reported_result` 永远不会被当作删除证明；
  发现/验证必须引用真正体现该状态的证据文件（`file_id`）或活动/审计 id。
- **副本漂移**：SQL 快照包含主库、区域副本、报表副本和故障转移副本；副本里的
  残留是真实的发现，不是噪声。
- **负证据**：能证明记录*缺席*的快照可以支撑 `VERIFY_RECORD_ABSENT` 步骤——
  当来源是权威快照时，缺席本身就是一种状态事实。
- **OCR 降级**：在非 macOS 机器上 `--skip-images` 会跳过 PNG；只存在于截图中的
  事实将不可得。我们披露准确性影响，而不是猜测（不编造任何内容）。

## 5. 身份关联（当前 + 历史标识符）

- 在 `user_identities.csv`（当前姓名/邮箱/电话/邮箱哈希）**和**
  `user_audit_log.csv`（历史邮箱/电话/邮箱哈希）之上建立统一索引。
- 把每个案例请求中的 `email`（可能是历史邮箱）解析为唯一的 `user_id`；
  对歧义显式报告/处理，而不是静默挑一个。
- 通过当前标识符、历史标识符、哈希、`resource_id` 模式、`system_id`、时间戳
  以及活动/证据中记录的事务链路，把证据观测关联起来。
- 为 `audit_at` 之后采集的证据保留一条*静态*关联通道（仅身份，绝不含状态）。
- 已知难点：完全匿名化的分析画像会丢失所有直接标识符；归属只能依赖快照排序
  （位置关系）、活动时间窗和排除法。这是已披露的不确定性。

最终运行的身份解析（已对照数据集核实）：
**550/550 个案例全部唯一解析**——32 个公开样例 + 全部 518 个评测案例；
**0 个未解析**。518 个评测案例映射到 **517 个不同用户**（有一个人提交了两次
请求）。不存在静默回退：任何无法通过当前或历史邮箱解析的请求都会显式报错，
最终运行中一次也没有发生。

## 6. `audit_at` 时点重建

1. 确定案例的证据包：隐藏案例遵循波次（wave）证据结构，使用波次证据文件；
   手工构造的特殊案例使用专属 fixture 证据。
2. 把所有相关证据解析为带 `captured_at` 和来源 `evidence_id` 的观测。
3. 对每个资源，选择满足 `captured_at <= audit_at` 的最大 `captured_at` 观测
   （最新有效状态）；忽略更晚的证据对状态判断的影响。
4. 把重建出的状态与 `deletion_rules.csv` 比较（每个类别要求的动作，包括
   条件化的 REDACT/ANONYMIZE/RETAIN 与恢复拦截）。
5. 任何偏差 → `INCOMPLETE` 发现；否则 → 带证据支撑验证步骤的 `COMPLETE`。

我们显式处理的开放问题：副本滞后（哪份副本权威）、"主库已删但之后又同步回来"、
"允许存在的保留记录"，以及只允许保留稳定 `user_id` 的墓碑记录。

## 7. 确定性与模型的分工（以及原因）

| 层 | 方案 | 原因 |
| --- | --- | --- |
| 证据解析 | 按格式的确定性解析器 | 可审计、可测试、相同输入 → 相同事实 |
| 身份解析 | 确定性索引 + 规则匹配 | 精确 id/哈希；可解释 |
| 状态重建 | 确定性"最新有效观测"规则 | 可复现；不幻觉出不存在的记录 |
| 策略/规划/排序 | 由 `deletion_rules.csv` + 题面得出的确定性表 | 评分器检查精确结构与顺序 |
| 意图分类 | 默认确定性多语言规则 | 删除 vs 非删除是契约决策，必须稳定 |
| 意图复核（可选） | DeepSeek 对话模型，temperature 0，带缓存 | 只复核/标记歧义请求文本；从不写事实 |

最终提交运行：`--llm-intent`（DeepSeek `deepseek-flash`，temperature 0），
共 **10 次调用**——恰好是 10 个低信号 `NON_DELETION` 案例
（case_533–case_542）。它是**顾问性**层：确定性分类器仍是权威，模型与之一致
**10/10**，且**没有任何案例结论或步骤因此改变**。响应按请求文本的 SHA-256
缓存在 `evaluation/intent_cache.json`（不含请求原文、不含密钥），随
`code.zip` 一起交付；因此模型层可以**离线零调用**重放。

离线确定性已实测：用 `--no-llm` 重跑同一命令，生成的 `output.csv`
**逐字节一致**（相同 SHA-256）。完整的实测模型/调用/token/成本表见
`evaluation/usage_report.md`。

## 8. 策略与修复规划

- `deletion_rules.csv` 把数据类别 + 条件映射为动作
  （DELETE / REDACT / ANONYMIZE / RETAIN / 墓碑 REDACT）。
- 计划构造：
  - **FINDING**（发现）：每个违规一项——`REPORT_REMAINING_RECORD`
    （本应删除但存在）、`REPORT_EXPOSED_PII`（可以保留但标识符未脱敏/匿名化）、
    `REPORT_ACTIVE_DATA_FLOW`（同步/导入可能重新制造数据）、
    `REPORT_RESTORE_RISK`（备份可能恢复数据）。
  - **REMEDIATION**（修复）：`DELETE_RECORD` / `REDACT_RECORD` /
    `ANONYMIZE_RECORD` / `DISABLE_DATA_FLOW` / `BLOCK_RESTORE`；
    数据流/恢复类动作先于依赖它的记录变更（操作顺序表强制执行这一约束）。
  - **VERIFICATION**（验证）：每个已修复记录/流程要求的最终状态，加上基线
    缺席检查；保留记录 → `VERIFY_RECORD_PRESENT`。
- 证据规则：发现引用参与者可见证据；COMPLETE 的验证引用证明当前状态的证据；
  INCOMPLETE 案例的修复步骤与修复后验证步骤使用 `evidence_id=""`。
- 排序：阶段 → 题面的操作顺序 → `system_id` → `resource_id`，
  实现为一个确定性排序。

最终输出规模（从提交的 `output.csv` 本身计算）：

| 项目 | 数值 |
| --- | --- |
| 行数 / 案例数 | 518（按数值 `case_id` 排序） |
| 总步骤数 | 3,242（其中 1,245 步引用证据；其余是未来的修复/验证步骤） |
| 计划中出现的不同系统 | 11（`search_service`、`account_service`、`support_platform`、`security_service`、`integration_service`、`analytics_platform`、`backup_service`、`export_service`、`identity_service`、`legal_service`、`marketing_platform`） |
| 15 种允许的操作 | 全部使用 |
| 状态分布 | `COMPLETE` 152、`INCOMPLETE` 356、`NOT_APPLICABLE` 10 |
| `NOT_APPLICABLE` 案例 | case_533–case_542（10 条非删除请求） |
| `output.csv` SHA-256 | `ea7ee8546a11981369bd606c72ec71f20331e2b8f9bacf017d8830d4b546eecb` |

`注意：以上计数均从提交文件本身计算；如果某处要求状态分布与另一份文档一致，
应更新那份文档——文件才是最终依据。`

## 9. 输出契约与自检

- `output.csv`：精确表头、518 行数据、按**数值** `case_id` 排序
  （`case_33, case_99, case_100, …, case_550`；不是字典序）、每行一个 JSON
  数组、`step_no` 连续、operation/state 组合合法、phase/排序规则、
  按状态区分的证据规则，并且引用的证据采集时间不晚于案例的 `audit_at`。
- 提交前自检：
  - `uv run python evaluation/evaluate.py validate --output output.csv ...`
    （独立契约校验器 + 证据 id/时间交叉检查）
  - `uv run python scripts/validate_submission.py --dataset <DIR>`
    （契约 + code.zip + submission/ + 密钥扫描）
  - `uv run pytest`
提交产物上的最终验证结果：

- `evaluation/evaluate.py validate --output output.csv ...`：
  **0 errors / 0 warnings**（518/518 行、自然/数值排序、每处引用都是存在于
  审计窗口内的真实 `file_id`/`activity_id`/`audit_id`）。
- `scripts/validate_submission.py --dataset <DIR>`：`output.csv` 契约
  **PASS**（0 errors）；`code.zip` 内容：必需条目齐全，不含 `dataset/`，
  不含缓存/虚拟环境，不含嵌套压缩包，不含凭据模式。
- `uv run pytest -q`：最终树上 **95 passed**；依赖官方数据集或流水线 CLI 的
  测试在缺失时以明确原因 skip（AGENTS.md 验收标准）。
- `sha256(output.csv)` = `ea7ee8546a11981369bd606c72ec71f20331e2b8f9bacf017d8830d4b546eecb`。
  确定性 `--no-llm` 重跑逐字节一致，且 `scripts/build_code_zip.py` 会打印最终
  归档 SHA-256（同一棵树两次构建完全一致）。

## 10. 评估

三个层次，独立性从高到低：

1. **单元/契约测试**（`tests/`）：数据集加载、身份解析、策略映射、证据解析器、
   输出契约、排序、变异测试。
2. **独立评估器**（`evaluation/evaluate.py`，不 import 答案生成流水线）：
   严格输出契约校验；官方 32 案例公开样例回归；团队手写期望答案的自建案例
   （`evaluation/cases/`）；输入变换（行乱序、诱饵记录、仅改 `reported_status`）
   与变异检查。
3. **官方样例回归**（`evaluation/evaluate.py samples`）：32 个公开案例上的
   开发回归证据——**不是**隐藏集准确率声明。

实测结果来自最终评估报告（`evaluation/evaluation_report.md`，在
2026-10-25T03:51Z 最终流水线运行后刷新）。公开样例列是**开发回归集**
（32 个有标注案例），**不是**隐藏集准确率声明：

| 指标 | 官方样例（32） | 团队案例（13） |
| --- | --- | --- |
| 案例级删除状态准确率 | **1.0000（32/32）** | **1.0000（13/13）** |
| 步骤级精确率（多重集） | 0.9476 | **1.0000** |
| 步骤级召回率（多重集） | 0.9378 | **1.0000** |
| 步骤级 F1 | 0.9427 | **1.0000** |
| 字段级准确率（总体） | 0.9682 | **1.0000** |
| 序列准确率（有序 `steps_json` 完全一致） | 0.7500（24/32） | **1.0000（13/13）** |
| 证据匹配准确率 | **1.0000**（177 个匹配的处理位置） | **1.0000** |
| 契约错误 | 0 | 0 |
| 全量 `deletion_requests.csv`（518） | 仅契约：0 errors / 0 warnings（无公开标注） | — |

其他实测检查：

| 检查 | 结果 |
| --- | --- |
| 序列准确率（样例） | 0.7500（24/32） |
| 有序处理准确率（样例，仅看顺序） | 0.7500（24/32） |
| 变换测试（行乱序 / reported_status 翻转 / 诱饵） | 6/6 通过（逐案例预测不变） |
| 评估器变异测试（盲信声明、忽略历史邮箱、漏修复、错误顺序、错误操作） | 5/5 被检出 |
| 产出 `output.csv` 的契约校验 | 0 errors / 0 warnings |
| 团队自建评估案例 | 13 个（手写期望答案；见 `evaluation_report.md` §4） |

最终全量运行：518 行、3,242 步，契约 **0 errors / 0 warnings**
（隐藏标准答案不公开，因此 518 案例输出只做契约检查、不做准确率评分）。
评估 harness 报告：`evaluation/reports/sample_report.{json,md}` 与
`evaluation/reports/cases_report.{json,md}`。

## 11. 发现的失败与改进（诚实复盘）

有两次测量发生在流水线仍在修复时；最终树（冻结提交）产生第 10 节的指标：

| 测量 | 状态准确率（样例） | 步骤 F1 | 精确序列 | 失败样例数 |
| --- | --- | --- | --- | --- |
| 首次运行（12:45） | 1.0000 | 0.9378 | 0.6875 | 10/32 |
| 刷新（12:48） | 1.0000 | 0.9427 | 0.7500 | 8/32 |

最终树剩余的样例集失败**全部是步骤级**（没有状态级），并已逐案例记录在
`evaluation_report.md` §5：

- 匿名 analytics 归属（`case_03`：`analytics_9406` vs `analytics_5589`）；
- 波次 account/audit 基线分配与链式关联（`case_04`、`case_18`、`case_20`、
  `case_23`、`case_28`、`case_29`）；
- support 记录分类（`case_10`：没有共享上下文证据时，标准答案 DELETE vs
  预测 REDACT）。

由 harness 已验证的改进：

- 契约：产出的 `output.csv` 通过严格校验器，0 errors / 0 warnings（518 行、
  规范排序、每处引用都是审计窗口内的真实 `file_id`/`activity_id`/`audit_id`）；
- 状态决策：公开样例 100%、13 个独立案例全部正确，包括 NOT_APPLICABLE 访问请求；
- 声明独立性：行乱序、`reported_status` 翻转和诱饵记录不改变任何逐案例预测
  （6/6 变换测试）；
- 早期开发中的匿名 analytics 过度上报（`case_09`、`case_24`–`case_26`）在
  流水线修改后消失；精确序列准确率从 0.6875 升到 0.7500；
- 证据纪律：样例证据准确率 1.0000，citation-window 案例证明
  `audit_at` 之后的文件从不被引用；
- 评估器有效性：5/5 变异测试被检出，说明指标不是空洞的。

这些是诚实的最终数字：两个公开回归集上的状态决策全部正确，而 32 个公开样例的
步骤/序列准确率是 0.9427 F1 / 0.7500 精确序列。失误集中在结构性归属歧义
（匿名 analytics 行、波次 account 基线、support 消息 vs 附件），而不在删除/
保留策略逻辑；团队自建案例把规则完全钉死（13/13）。契约层干净
（0 errors / 0 warnings），证据窗口处处得到遵守。

## 12. 成本、性能与已知限制

最终全量运行实测：

| 项目 | 数值 |
| --- | --- |
| 模型提供方 | DeepSeek（`https://api.deepseek.com`） |
| 模型名称 | `deepseek-flash`（运行时校验；唯一调用的模型） |
| 模型调用次数 | 10（仅 10 个低信号意图案例；预算 40） |
| 输入 token | 1,493 |
| 输出 token | 340 |
| 总 token | 1,833 |
| 每个被复核案例的平均 token | 183.3 |
| 每个数据集案例（518）的平均 token | 3.54 |
| 估算总成本 | USD 0.00042795 |
| 每个数据集案例的估算成本 | USD 0.00000083 |
| 价格假设 | off-peak USD 0.15 / 1M 输入、USD 0.60 / 1M 输出（DeepSeek 公开定价，记录于 2026-10-25；运行时间 03:51Z 周日 = off-peak） |
| 墙钟运行时间（518 案例） | 总计 12.5 s（确定性核心约 2.5 s + 10 次顺序模型调用约 10 s） |
| 证据吞吐 | 94 个证据文件 → 2,922 条观测，0 条解析器警告 |
| 缓存重跑 | 随包提供 `evaluation/intent_cache.json` → `--llm-intent` 重跑 **0** 次模型调用；`--no-llm` 重跑逐字节一致 |

已知限制：

- 隐藏标准答案不可得；公开样例分数是开发回归，不构成隐藏集承诺。
- 匿名 analytics 归属是启发式的（快照排序、活动时间窗、排除法）；少量资源 id
  可能不同。
- PNG 截图需要 macOS Vision；`--skip-images` 会减少可用事实。
- 系统只报告所给证据支持的内容；当证据沉默时不虚构状态。

## 13. 可能的面试问答

1. **"这道题里'删除完成'是什么意思？"**
   每一份相关副本都得到策略要求的处置（delete/redact/anonymize/retain）；没有
   活跃的同步/导入/恢复链路可以重新制造数据；保留记录只含允许的标识符；应当
   保留的记录仍然可用。
2. **"你如何判定 COMPLETE 还是 INCOMPLETE？"**
   把重建的 `audit_at` 时刻每资源状态与 `deletion_rules.csv` 做确定性比较；
   任何偏差或再生路径 → INCOMPLETE 并给出发现；否则 → COMPLETE 并附证据支撑
   的验证步骤。
3. **"幽灵数据难在哪里？"**
   声明 vs 证明、当前 vs 历史标识符、副本漂移、会重新制造已删数据的备份与同步
   任务、必须保留稳定引用的墓碑记录，以及看起来像残留但其实是必须保留的记录。
4. **"你如何避免幻觉证据？"**
   LLM 不在事实路径上。解析器产出带 `evidence_id` + `captured_at` 的类型化观测；
   规划器只引用真实存在且满足 `captured_at <= audit_at` 的观测，并由两个独立
   检查器验证。
5. **"历史标识符有什么用？"**
   请求可能使用旧邮箱；旧标识符仍可能出现在日志、支持附件或副本中，因此必须索引
   `user_audit_log` 才能找到每一份副本。
6. **"你如何处理滞后的副本？"**
   每个 SQL 快照都按其快照时间解析；`audit_at` 时刻的状态取最新有效快照，但副本
   中的残留仍是真实发现，因为它们可能恢复或暴露数据。
7. **"为什么不让 LLM 生成步骤？"**
   评分契约是精确的（操作、状态、顺序、证据规则）。把模型放进这条路径会不可
   复现并且可能编造事实；我们的 LLM 只限于复核歧义意图文本，并带响应缓存。
8. **"没有隐藏答案你怎么评估？"**
   单元/契约测试、独立评估器、32 个公开样例回归、手写期望答案的团队案例、
   输入变换，以及证明评估器能抓住典型 bug 的变异测试。
9. **"最强的失败模式是什么？"**
   在 32 个公开样例上实测（全部步骤级，没有状态级）：
   (a) 匿名 analytics 归属——匿名画像的行被关联到错误用户（`case_03`）；
   (b) 多个案例共享一个波次时的 account/audit 基线配对（`case_04`、`case_18`、
   `case_20`、`case_23`、`case_28`、`case_29`）；
   (c) support 记录分类——没有共享上下文证据时消息 vs 附件的处置（`case_10`）。
   契约与证据窗口失败：最终运行没有。
10. **"如果给你更多时间/数据你会做什么？"**
    (a) 针对上面三类歧义补充更多独立案例（匿名 analytics、多案例波次基线、
    support 共享上下文）；(b) 利用 `system_activity` 中的更多跨系统链路加强归属；
    (c) 之后才考虑把顾问性意图复核扩展到有界 10 案例预算之外——当前 10 次调用
    成本约 USD 0.00000083/数据集案例，所以成本不是瓶颈，证据歧义才是。
11. **"成本如何控制？"**
    确定性流水线每个案例只跑一次、零模型成本；模型是可选的、temperature 0、
    有预算上限且带缓存。最终运行：10 次调用、1,833 tokens、总成本
    **USD 0.00042795 ≈ USD 0.00000083/数据集案例**。`--no-llm` 是零成本离线
    基线，产出逐字节一致的 `output.csv`。
12. **"如何保证可复现？"**
    `uv.lock` 固定 Python/依赖，确定性排序/序列化，决策中无墙钟/随机性，缓存
    LLM 响应，确定性 zip 构建，并且 README 中有从 `code.zip` 开始的干净目录
    复现步骤。
13. **"你怎么知道提交里没有数据集或密钥？"**
    `scripts/build_code_zip.py` 有显式排除清单 + 断言，`scripts/
    validate_submission.py` 独立扫描归档条目中的 `dataset/`、缓存、嵌套压缩包、
    `sk-` 密钥、凭据赋值和私钥。
14. **"运行时间和规模化故事？"**
    最终全量运行：518 案例 **12.5 s**（确定性核心约 2.5 s；10 次顺序模型调用
    约 10 s）。确定性证据解析与证据规模线性相关，计划按案例计算，模型调用可选、
    有预算上限且带缓存，流水线按案例无状态——更多案例只是算力问题，无需重新设计。
    从随包 `evaluation/intent_cache.json` 重跑是零模型调用，还会更快。
15. **"已知不确定性记录在哪里？"**
    `docs/planning/` 决策日志（内部）、README "Costs and known limitations"、
    评估报告，以及本指南第 12 节。

## 14. 复现映射（给面试官）

| 声明 | 去哪里核对 |
| --- | --- |
| 安装 + 运行命令 | `README.md`（Setup / Run / Packaging 节） |
| 输出契约 | `README.md` "Output contract"、`problem_statement.md` |
| 确定性流水线 / LLM 分工 | `README.md` "Reproducibility"、上文第 7 节 |
| 评估指标 | `evaluation/evaluation_report.md` |
| token/成本数字 | `evaluation/usage_report.md` |
| 契约校验 | `scripts/validate_submission.py`、`evaluation/evaluate.py validate` |
| 打包排除清单 | `scripts/build_code_zip.py` docstring + `docs/planning/02-decisions.md` D13/D14/D15（内部） |
| 干净目录复现 | `README.md` "Clean-room reproduction" |

## 15. 最终验证门禁（提交产物上全部满足）

- [x] 最终运行以文档化命令 + `--llm-intent` 执行
      （10 次顾问性调用，确定性核心权威，10/10 一致）。
- [x] `output.csv`：518 行、数值 `case_id` 排序、SHA-256
      `ea7ee8546a11981369bd606c72ec71f20331e2b8f9bacf017d8830d4b546eecb`，
      契约 0 errors / 0 warnings；`--no-llm` 重跑逐字节一致。
- [x] 第 10 节指标从最终 `evaluation_report.md` 刷新；第 12 节数字与
      `evaluation/usage_report.md` 一致。
- [x] 第 11 节列出真实的剩余失败；没有编造事故。
- [x] Q9 / Q10 / Q11 / Q14 填入实测值；没有遗留占位符。
- [x] 第 3 节模块清单与 CLI 参数已对照交付代码核实。
- [x] `README.md` 记录数值 `case_id` 排序，并引用
      `evaluation/evaluation_report.md` 与 `evaluation/usage_report.md`。
- [x] `scripts/build_code_zip.py` + `scripts/validate_submission.py` 在最终树上
      运行；校验器确认打包的报告、必需条目、无 dataset、无缓存/虚拟环境、
      无嵌套压缩包、无凭据模式。
- [ ] 仅 Lead 负责（在本指南之外）：把 `INTERVIEW_GUIDE.md`、`output.csv`、
      `code.zip` 和 `log.txt` 复制进 `submission/`，并最后再跑一次
      `scripts/validate_submission.py --dataset <DIR>` 门禁。
