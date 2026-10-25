# 01 — Task log (append-only)

本项目运行日志（工作过程记录），用于审计“谁在什么时候做了什么、结果是何状态”。
规则：

- **只追加，不改写历史**。新事件一律追加到文件末尾，带 ISO-8601 UTC 时间戳。
- 若某条早期判断后来被推翻，新增一条条目说明更正（保留旧条目）。
- 不记录任何密钥、API key、个人隐私数据。
- 本文件不进入 `code.zip`（打包脚本排除 `docs/`）；`log.txt` 才是提交给 HackerRank 的 chat transcript。

时间均为 UTC（本机时区 Asia/Tokyo，= UTC+9）。

## 任务拆分（来源：`docs/planning/00-design.md` §6，随实现更新）

| # | 任务 | 负责人 | 验收 | 当前状态 |
| --- | --- | --- | --- | --- |
| 1 | 仓库/文档/GitHub issue+Project/branch 脚手架 | Lead | issues 与 Project 条目存在；docs 可读 | 进行中（本地脚手架已就绪：`AGENTS.md`、`docs/planning/00-design.md`、`log.txt`） |
| 2 | 证据解析层（`evidence/*`、`activity.py`） | evidence-parser | 95 个证据文件可解析；pytest 覆盖格式；无静默跳过 | 进行中（`src/ghost_audit/evidence/` 已建立：base/logs/records/result/_util） |
| 3 | 身份解析 + intent 分类 | Lead | 518 case 全部唯一解析；10 个非删除意图识别正确 | 进行中（`identity.py`、`intent.py` 已存在） |
| 4 | 场景重建 + policy + planner + CLI | Lead | 32 样例 status 100%、steps 结构/顺序/字段匹配；输出契约通过 | 进行中（`scenario.py`、`policy.py`、`planner.py`、`output.py` 已存在；CLI 待落地） |
| 5 | 独立评估案例 + 变换测试 + 变异测试 + 契约校验 | eval-harness | 每个案例有独立手写期望与理由；故意 bug 能被测试发现 | 进行中（`evaluation/evaluate.py`、`evaluation/cases/` 已建立） |
| 6 | 全量 518 运行 + output.csv | Lead | 518 行、排序、契约、证据有效性自检 | 待开始 |
| 7 | 评估/用量报告、README、INTERVIEW_GUIDE、code.zip、submission 打包 | docs-packaging | 从干净目录解压可复现；实测 token/费用 | 进行中（README/构建脚本/校验脚本已完成并自测；报告与最终打包待评估数据） |
| 8 | GitHub PR/CI/merge、最终审计 | Lead | CI 绿；PR 已审阅合并；远端状态与本地一致 | 待开始 |

## 事件记录

### [2026-10-25T03:20:53Z] SESSION START — lead

- **Agent**: lead（Team Lead）
- **Actions**: 初始化仓库工作规则 `AGENTS.md`；建立 `log.txt`；读取官方参考仓库（problem_statement、AGENTS、README、dataset 目录结构）。
- **Context**: 启动 HackerRank Orchestrate October 2026「Ghost Data Still Exists」交付项目；确认官方 deadline 未配置，不虚构。
- **Status**: 完成（后续以 00-design.md 与任务板为准）。

### [2026-10-25T03:28:00Z] 设计文档 v0.1 + 仓库骨架

- **Owner**: lead
- **Actions**: 产出 `docs/planning/00-design.md`（问题理解/数据事实/策略/架构/任务拆分/评估计划/风险与已决定事项）；建立 `src/ghost_audit/`、`tests/`、`evaluation/`、`scripts/`、`submission/` 骨架；更新 `pyproject.toml`/`uv.lock`/`.gitignore`。
- **Context**: 设计已覆盖 518 case 的数据集事实（身份唯一解析、wave 证据结构、10 个非删除意图、证据格式族）、处置规则表、32 样例反推的 steps 生成规则。
- **Follow-ups**: GitHub issue/Project/branch 由 Lead 负责；各 teammate 按 task board 认领。
- **Status**: 完成。

### [2026-10-25T03:33:00Z] SESSION START — evidence-parser

- **Agent**: evidence-parser
- **Actions**: 认领 task-1（证据解析层），开始实现 94/95 个证据文件的解析。
- **Status**: 进行中。

### [2026-10-25T03:33:00Z] SESSION START — docs-packaging

- **Agent**: docs-packaging
- **Actions**: 认领 task-3；读取 `AGENTS.md`、`00-design.md`、官方 `problem_statement.md` / `README.md` / `AGENTS.md` §6.8–6.9、dataset CSV 头与 `sample_output.csv` 结构。
- **Context**: 开始 docs/packaging 工作流：README、确定性 `code.zip` 构建脚本、提交校验脚本、planning 日志、`INTERVIEW_GUIDE.md` 骨架。
- **Status**: 进行中。

### [2026-10-25T03:38:00Z] docs-packaging：校验脚本完成并自测 21/21

- **Owner**: docs-packaging
- **Actions**:
  - 新增 `scripts/validate_submission.py`（仅 stdlib）：output.csv 合同（518 行/排序/状态/7 字段/枚举/步号/phase 与 phase 内顺序/NOT_APPLICABLE、COMPLETE、INCOMPLETE 语义/证据规则）、`--dataset` 交叉校验（case 覆盖、evidence_id 存在性、captured_at <= audit_at）、`code.zip`（禁 dataset/venv/cache/嵌套压缩包/密钥、必需条目）、`submission/` 四项交付物与 `log.txt` 格式、退出码 0/1/2 与 `--skip-missing`。
  - 新增 `scripts/build_code_zip.py`：固定时间戳 + 排序 + 双次构建字节比对（确定性）、dry-run、必需条目与禁止路径断言、SHA-256 输出。
  - 新增 `README.md`（英文，含 uv 缓存、dataset 不打包、运行命令、OCR 回退、复现、评估命令、打包校验、许可与归属）。
  - 在 `work/` 下建立私有自测脚本（不随包提交），对 sample_output.csv 派生 fixture 做 21 个正/负例断言。
- **验证**: 自测 21/21 通过；当前仓库（尚无 output.csv/evaluation 报告）上默认运行返回 exit 2 并给出可操作缺失信息，`--skip-missing` 返回 exit 0。
- **Open TODOs**: evaluation 报告与 `INTERVIEW_GUIDE.md` 的实测数字待最终运行；CLI `cli.py`/`__main__.py` 待 Lead 落地后复跑校验。
- **Status**: 进行中（打包脚本与 README 主体完成）。

### [2026-10-25T03:41:00Z] docs-packaging：README / planning 文档 / INTERVIEW_GUIDE 骨架完成

- **Owner**: docs-packaging
- **Actions**:
  - `README.md` 完成（英文）：uv + `UV_CACHE_DIR` setup、dataset 不打包说明、最终运行与离线运行（`--llm-intent` / `--no-llm`）、`--sample`、PNG OCR 与 `--skip-images` 精度影响、输出合同与排序/证据规则、复现性、评估命令（pytest / `evaluation/evaluate.py validate|samples|cases|regress`）、打包与校验命令、干净目录复现、仓库布局、密钥管理、成本与已知限制、HackerRank 归属。
  - `docs/planning/01-tasklog.md`：任务表（00-design §6）+ 按时间戳的事件记录（追加式）。
  - `docs/planning/02-decisions.md`：D01–D20 决策（数据/证据、策略/规划/输出、打包/提交）+ 待核实事项 O1–O6。
  - `docs/planning/03-submission-checklist.md`：官方提交要求逐项清单（A–I 节，含复核命令与干净目录复现）。
  - `INTERVIEW_GUIDE.md`：面试指南骨架（问题理解/架构/证据/身份/时点重建/确定性 vs 模型/策略/评估/失败与改进/成本/15 个 Q&A/复现映射），所有实测数字用 `TBD (filled from the final full run)` 占位，未编造任何指标。
- **验证**:
  - `scripts/build_code_zip.py --dry-run --allow-missing`：213 个文件、467.8 KiB、两次构建 byte-identical、SHA-256 输出；确认 `dataset/`、`docs/`、`work/`、`__pycache__`、`.ocr-cache` 等均被排除。
  - 真实写包测试：`--allow-missing --output work/...` 两次构建 `cmp` 相同；`validate_submission.py --zip` 正确报出缺失的 evaluation 报告与入口点（符合当前开发阶段）。
  - 校验脚本自测保持 21/21 通过；新增对带前缀的 `DEEPSEEK_API_KEY="…"` 字面量赋值检测。
  - `evaluation/evaluate.py validate` 对官方 `sample_output.csv`（32 行）无合同错误（仅行数/覆盖不匹配，因其不是 518 行 hidden 输出）。
- **Open TODOs**: `cli.py`/`__main__.py`、`evaluation/evaluation_report.md`、`evaluation/usage_report.md`、`output.csv` 尚未就绪；`INTERVIEW_GUIDE.md` 的 TBD 需 Lead 用最终运行数据填充；README 中 flag 名称需在 CLI 落地后复核。
- **Status**: 主体完成，等待最终运行数据与 CLI。

### [2026-10-25T03:47:00Z] docs-packaging：CLI 落地、README 与脚本对齐、当前 output.csv 合同通过

- **Owner**: docs-packaging
- **Actions**:
  - Lead 落地 `src/ghost_audit/{cli,__main__,llm}.py`，`pyproject.toml` 项目名改为 `ghost-audit`；`uv run python -m ghost_audit run --help` 可用。
  - 按真实 CLI 修订 README：删除未实现的 `--evidence-cache`，补充 `--emit-blueprint`/`--quiet`，明确 `--dataset` 在干净环境必须显式传入（编译默认值仅指向本地 docs/refs 参考仓库），`--no-llm` 为实际默认（仅 `--llm-intent` 才调用模型），依赖说明改为仅 pypdf。
  - 校验当前 `output.csv`（12:46 版，518 行）：合同 PASS（排序、覆盖、step 结构/顺序、证据规则、evidence_id 存在性与 `captured_at <= audit_at` 全部通过）；分布 COMPLETE=152 / INCOMPLETE=356 / NOT_APPLICABLE=10。
  - `evaluation/evaluate.py validate` 对同一 `output.csv` 独立复核：0 error / 0 warning（与 `scripts/validate_submission.py` 结论一致）。
  - `build_code_zip.py --dry-run`：262 files / 813 KiB；入口点 OK；仅缺两份必需 evaluation 报告。
  - 在 `work/docs_packaging/templates/` 准备 `evaluation_report.md` / `usage_report.md` 结构模板（TBD 占位，不随包），供 Lead/eval-harness 填实测数据。
- **发现并反馈**: 12:45 版 output.csv 曾有 10 个合同错误（case_63 COMPLETE 空数组、8 个 COMPLETE 验证步缺证据、case_126 FINDING 缺证据），12:46 版已修复；已通过消息反馈 Lead。
- **Status**: 完成度提高；等待最终全量运行、两份 evaluation 报告、INTERVIEW_GUIDE 实测数字与 submission/ 四个交付物。

### [2026-10-25T03:52:00Z] docs-packaging：按 Lead 最终规则更新排序/打包/README/面试指南

- **Owner**: docs-packaging
- **决策来源**: Lead 消息（最终运行命令、排序规则、code.zip 内容规则、GitHub flow 分工）。
- **Actions**:
  - `scripts/validate_submission.py`：行序检查改为 **数值 case 序号**（`case_33, case_99, case_100, …, case_550`），字典序现在会报错；docstring/错误信息同步更新；新增对 evaluation 报告中 `TBD/TODO` 占位符的警告扫描。
  - `scripts/build_code_zip.py`：新增打包 `evaluation/intent_cache.json`（推荐条目）、排除 `evaluation/llm_usage.jsonl`、`evaluation/.tmp/**`；保留 `.ocr-cache/`、`work/`、`src/*/config/`、`api_key.txt`、`output.csv`、`log.txt` 排除；自测脚本新增“数值排序接受 / 字典序拒绝”两个用例（23/23 通过）。
  - `README.md`：排序改为“canonical numeric order”并说明非字典序；`--llm-intent` 明确为 review-only（不改变审计结论）；说明 intent cache 随包、`llm_usage.jsonl` 不随包、干净数字进 usage_report；打包排除清单同步。
  - `INTERVIEW_GUIDE.md`：用 `evaluation/evaluation_report.md`（12:48 refresh，真实数据）填充 §10 指标表（samples status 32/32、step F1 0.9427、sequence 0.7500、field 0.9682、evidence 1.0000；13 个自建案例全对）、§11 失败与改进；§12 模型 provider/name 填入 DeepSeek/deepseek-chat，token/成本/耗时仍留 `TBD` 等最终运行。所有待填项保留 `TODO(lead)` 便于 grep。
  - `docs/planning/02-decisions.md`：新增 D21（数值排序）、D22（intent cache 打包/telemetry 排除）。
- **验证**: selftest 23/23；当前（字典序旧版）`output.csv` 会被新行序检查正确报错，等 Lead 重新生成数值序版本；build dry-run 仅缺 `evaluation/usage_report.md`。
- **Status**: 等待 Lead 最终运行重生成 output.csv + usage_report，然后最终 build/validate 并报告 SHA-256。

### [2026-10-25T03:55:00Z] docs-packaging：最终运行数据回填、README/INTERVIEW_GUIDE 定稿、code.zip 构建与校验

- **Owner**: docs-packaging
- **Actions**:
  - 用 Lead 提供的最终运行事实（`--llm-intent`、output.csv SHA-256 `ea7ee854…`、12.5 s、94 evidence files→2,922 observations、samples/13 cases 指标、模型 deepseek-flash 10 calls/1,493 in/340 out/1,833 tokens/USD 0.00042795）回填 `INTERVIEW_GUIDE.md` 全部 `TODO(lead)`/`TBD`，并补充最终输出规模（518 行、3,242 steps、11 systems、15 operations、状态分布）；移除占位 banner，明确“模型仅 advisory、审计确定性、32 samples 为开发回归集”。
  - `README.md` 新增 “Final run at a glance” 表（命令/518 行/SHA/合同 0-0/复现性/samples 与 13 cases 指标/模型用量/耗时）；确认 numeric case_id 排序与两份报告引用。
  - 最终构建 `submission/code.zip`：240 files、795.0 KiB uncompressed、257,844 bytes compressed、sha256 `7f8bff15e144d4f13934dbc490406e68d52692428c00081abd5ba9cb9b5562e1`，确定性双构建一致、写后重开验证 240 entries。
  - 校验：`evaluation/evaluate.py validate` 0 errors/0 warnings；`scripts/validate_submission.py --dataset …` 对 output.csv/dataset 交叉校验/code.zip 全 PASS，仅 `submission/` 尚缺 output.csv、log.txt、INTERVIEW_GUIDE.md（Lead 负责复制）→ exit 2；`--skip-missing` PASS（3 warnings）；`uv run pytest -q` = 95 passed。
  - 说明：最终 output.csv 实际状态分布为 COMPLETE=152 / INCOMPLETE=356 / NOT_APPLICABLE=10（与 Lead 消息中的 153/355 不一致；文件 SHA 与 Lead 给出的一致，以文件为准并已在面试指南注明“computed from submitted file”）。等待 Lead 确认。
- **Status**: docs-packaging 交付完成；剩余为 Lead 的 submission/ 复制与最终 gate。
