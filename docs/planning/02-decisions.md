# 02 — Decision log

本文件记录项目中的**已做决定**及其理由与备选方案。编号 `D##` 只增不改；若决定被推翻，
新增一条决定并注明 supersedes 关系（旧条目保留）。
来源：`docs/planning/00-design.md` §3/§4/§5/§8 的既有决定 + 本轮 packaging 决定。
本文件不进入 `code.zip`（打包排除 `docs/`）。

格式：每条 = 决定 / 理由 / 备选与为何未选 / 影响与后续。

---

## A. 数据与证据

### D01 — 只使用 participant-facing 文件
- **Status**: accepted（2026-10-25）
- **Decision**: 运行时仅读取 `<dataset>/` 中题面列出的 participant-facing 文件；绝不读取 organizer-only truth、golden answers 或 generator internals。
- **Rationale**: 挑战规则明确禁止；且 hidden canonical 不可得，任何利用 organizer 真值的路径都属违规 shortcut。
- **Alternatives**: 从样例反推 hidden 答案（违规）；硬编码 case 家族映射（违规且不可泛化）。
- **Consequences**: 准确率上限受证据覆盖限制；在 README/评估报告中如实披露不确定性。

### D02 — claim 不是 proof：必须重建 `audit_at` 时刻状态
- **Status**: accepted（2026-10-25）
- **Decision**: `reported_status`、`reported_at`、`system_activity.reported_result` 仅视为 claim；状态由 `captured_at <= audit_at` 的证据决定。
- **Rationale**: 题面核心陷阱即“workflow 显示 Complete 但数据仍在”；样例回归也验证了 claim 与真实状态大量不一致。
- **Alternatives**: 直接采信 `reported_status`（会导致系统性错误）；对 claim 与证据取多数票（无理论依据）。
- **Consequences**: 需要完整证据解析层（task-1）与按时间窗的状态重建（scenario.py）。

### D03 — 晚于 `audit_at` 的证据只用于静态身份关联
- **Status**: accepted（2026-10-25）
- **Decision**: `captured_at > audit_at` 的证据不得支撑 finding/verification；仅可作为“该 resource 属于该 user”的静态身份线索，并在设计/评估文档中披露。
- **Rationale**: 题面要求“只用 `audit_at` 之前的信息决定该 case”；但身份链接与时间点无关，README/AGENTS 亦允许 static identity linking。
- **Alternatives**: 完全忽略晚于 audit_at 的证据（会丢失少量匿名记录归属线索）；允许其影响状态（违规）。
- **Consequences**: `scripts/validate_submission.py` 与 `evaluation/evaluate.py` 都会检查“引用证据 captured_at <= audit_at”。

### D04 — 身份解析：current snapshot + user_audit_log 历史标识符
- **Status**: accepted（2026-10-25）
- **Decision**: 用 `user_identities.csv` 与 `user_audit_log.csv` 建立 current + historical email/phone/email_hash 索引；case → user 通过请求 email（可能是历史 email）唯一解析。
- **Rationale**: 已核实 518 个请求 email 全部可唯一解析（含 32 样例）；历史邮箱是“ghost data”的主要来源之一。
- **Alternatives**: 只匹配 current email（会漏支持历史邮箱的残留副本）；模糊匹配姓名（样例中重名/多音字会误配）。
- **Consequences**: `identity.py` 必须先于证据归属；解析失败必须显式报错而非静默丢弃。

### D05 — 证据选择：同资源取 `captured_at` 最大且 `<= audit_at` 的记录
- **Status**: accepted（2026-10-25）
- **Decision**: 同一 resource 在同 case 下有多条候选观察时，选 `captured_at` 最新且仍不晚于 `audit_at` 者；由样例 32/32 反推验证。
- **Rationale**: 更能反映“audit 时刻”的真实状态（如 `account_8473` FOUND→NOT_FOUND 的演变）。
- **Alternatives**: 取最早证据（会看不到删除后的状态）；取所有证据集合求交（无法解释副本漂移）。
- **Consequences**: 副本（failover/read/regional/reporting）滞后需按“主库 vs 副本”漂移解释，不能简单取并集。

### D06 — wave 证据包重建场景
- **Status**: accepted（2026-10-25）
- **Decision**: 对 hidden 主体 case，用“每个 wave 恰有一个 wave 证据文件”的结构重建该 wave 内 case 的场景；零散日期 case 用其专用证据包。
- **Rationale**: 已核实 wave 结构（同 wave 的 audit_at 同日、证据覆盖该 wave ≥3/4 的 case 用户）。
- **Alternatives**: 只按单个 resource 精确匹配（wave 证据包以快照形式给出，需要按用户判断“存在/不存在”）。
- **Consequences**: 场景重建需要把“快照中不存在”也当作一种可引用的事实（负证据），并选择合适证据文件。

---

## B. 策略、规划与输出

### D07 — `deletion_rules.csv` 决定 category → action
- **Status**: accepted（2026-10-25）
- **Decision**: 以规则表为准：DELETE / REDACT / ANONYMIZE / RETAIN / tombstone-redact；findings/remediation/verification 由规则 + 当前状态推导，不按 case 家族特判。
- **Rationale**: 规则表是题面提供的唯一授权策略来源；sample 32/32 与之一致。
- **Alternatives**: 从样例硬编码 case→steps（不可泛化，违反规则）；按“数据类别直觉”处理（会与 RETAIN/REDACT 条件冲突）。
- **Consequences**: `policy.py` 维护规则映射；必须保留的记录输出 `VERIFY_RECORD_PRESENT`，不得误删。

### D08 — 排序合同：phase → 操作表顺序 → `system_id` → `resource_id`
- **Status**: accepted（2026-10-25）
- **Decision**: 严格按题面：FINDING→REMEDIATION→VERIFICATION；phase 内按操作表顺序；再按 `system_id`、`resource_id` 升序。
- **Rationale**: 题面明确“array order is significant”；32 样例 100% 符合。
- **Alternatives**: 只按发现顺序输出（会失分）；按 step_no 排序后再调整（等价于本决定）。
- **Consequences**: 输出前做确定性排序；`validate_submission.py`/`evaluate.py` 双重校验。

### D09 — 证据引用规则
- **Status**: accepted（2026-10-25）
- **Decision**: FINDING 必须引用 `file_id`/`activity_id`/`audit_id`；COMPLETE 的 VERIFICATION 引用证明当前状态的证据；INCOMPLETE 的 REMEDIATION 与未来 VERIFICATION 一律使用空 `evidence_id`。
- **Rationale**: 题面原文；样例 32/32 符合（118 个空 evidence 全部出现在未来工作 step）。
- **Alternatives**: INCOMPLETE 的 remediation 引用“当前证据”（与题面不符且样例不支持）。
- **Consequences**: planner 生成两类 step 时证据字段规则不同，必须分开处理。

### D10 — 确定性优先，模型只做窄用途 intent 复核
- **Status**: accepted（2026-10-25）；最终 `--llm-intent` 为可选
- **Decision**: 证据解析/身份/状态重建/策略/规划/序列化全部确定性；模型仅用于多语言删除意图的复核/标记（temperature 0、响应缓存、记录 usage）。默认 `--no-llm`，无 API key 也能完整运行。
- **Rationale**: 评分重事实与顺序正确性；LLM 引入不确定性与成本，收益只在 intent 语义。
- **Alternatives**: 用 LLM 直接生成 steps（不可复现、易失败、成本高）；完全不用模型（可以，但题面鼓励 AI agent，且多语言 intent 有边界情况）。
- **Consequences**: `evaluation/usage_report.md` 必须记录模型/调用/token/费用；`--llm-intent` 的模型名 deepseek-chat 与价格假设需在报告中注明。

### D11 — LLM 响应缓存用于可复现
- **Status**: accepted（2026-10-25）
- **Decision**: `--llm-intent` 的响应写入 `evaluation/intent_cache.json`（可 `--intent-cache` 覆盖）；同缓存重跑不重复请求。
- **Rationale**: 复现性与成本控制；使最终运行有可审计的输入/输出映射。
- **Alternatives**: 不缓存（重跑结果可能漂移、费用重复）；把缓存放 `work/`（不随包，不可复现）。
- **Consequences**: 缓存的 schema 必须稳定；缓存文件不得包含 key；打包脚本允许其进入 `code.zip`（属于 evaluation/），若过大再评估。

### D12 — OCR：macOS Vision，缺失时显式回退
- **Status**: accepted（2026-10-25）
- **Decision**: 11 张 PNG 用 `scripts/ocr_images.swift`（macOS Vision）转文本；无 Swift 工具链时提供 `--skip-images`，跳过截图的观察而非伪造事实；Linux CI 相关测试 skip。
- **Rationale**: 本机可用且质量高；不能要求评委机器一定有 macOS/OCR。
- **Alternatives**: 捆绑第三方 OCR 模型（体积/许可/离线复杂性）；忽略所有图片（丢失题面要求的多模态证据）。
- **Consequences**: README 明确说明 `--skip-images` 的精度影响；`.ocr-cache/` 不进入交付包。

---

## C. 打包与提交（本轮 docs-packaging 决定）

### D13 — `code.zip` 内容清单
- **Status**: accepted（2026-10-25）
- **Decision**: 打包 `README.md`、`INTERVIEW_GUIDE.md`（若存在）、`pyproject.toml`、`uv.lock`、`.python-version`、`src/**`、`tests/**`、`evaluation/**`（含两份必需报告）、`scripts/**`；`submission/code.zip` 由 `scripts/build_code_zip.py` 生成。
- **Rationale**: 题面要求 runnable solution + README + evaluation/ 报告；保持 archive 根目录与仓库结构一致，便于 `uv sync` 后按 README 运行。
- **Alternatives**: 把代码放进 `code/` 子目录（官方 starter 布局，但本仓库是 src 布局，改成 code/ 反而要移动源码）；只打源码不打 tests（会降低可信度）。
- **Consequences**: `code.zip` 根目录直接是项目根；`uv run python -m ghost_audit run ...` 与 README 一致。

### D14 — `code.zip` 排除清单（硬约束）
- **Status**: accepted（2026-10-25）
- **Decision**: 排除 `dataset/`、`docs/`（含 `docs/refs/` 只读参考仓库）、`submission/`、`work/`、`.venv`、`.git`、`.uv-cache`、`.ocr-cache`、`__pycache__`、`.pytest_cache`、`log.txt`、`output.csv`、`.env`、`.DS_Store`、`api_key.txt`、`src/*/config/`（本地密钥目录）、任何嵌套压缩包（`.zip/.tar/.gz/.tgz/.7z/.rar/.whl`）。
- **Rationale**: 题面/参考 AGENTS §6.9 明确禁止 dataset、virtualenv、cache、nested archive、API key；`log.txt` 是单独上传的 chat transcript，`output.csv` 是单独提交物。
- **Alternatives**: 用 `zip -x` 手工排除（不可审计、跨平台差异）；把 docs 一并打包（包含只读参考仓库，违规）。
- **Consequences**: `validate_submission.py` 会独立复核排除项；`build_code_zip.py` 有 guard 断言。

### D15 — 确定性打包
- **Status**: accepted（2026-10-25）
- **Decision**: archive 条目按路径排序；所有条目固定时间戳 `1980-01-01T00:00:00`、固定权限 `0644`、deflate level 9；构建两次并字节比较，输出 SHA-256。
- **Rationale**: 同一仓库状态下生成完全相同的包，便于审计“提交的包 == 本地验证的包”。
- **Alternatives**: 依赖系统 `zip`（时间戳/顺序不可控）；构建一次不做比较（无法证明确定性）。
- **Consequences**: 源码内容变化自然改变 SHA-256；CI 可校验包摘要。

### D16 — `submission/` 恰好四项交付物
- **Status**: accepted（2026-10-25）
- **Decision**: `submission/` 只放 `output.csv`、`code.zip`、`log.txt`、`INTERVIEW_GUIDE.md`；`log.txt` 由 Lead 从仓库根复制，docs-packaging 不生成/不改写它。
- **Rationale**: 题面提交表 + 团队分工（Lead 拥有 log.txt）；避免额外文件干扰评审。
- **Alternatives**: 把文档/报告额外复制进 submission（多余且可能泄露内部信息）。
- **Consequences**: `validate_submission.py` 检查缺失/多余项；多余项仅警告。

### D17 — 校验脚本 stdlib-only、可独立运行
- **Status**: accepted（2026-10-25）
- **Decision**: `scripts/validate_submission.py` 只用 Python 标准库，可用 `.venv/bin/python` 或系统 python3 运行；退出码 0=通过、1=校验错误、2=必需产物缺失；`--skip-missing` 允许开发期校验部分产物。
- **Rationale**: 需要在提交前做“与依赖无关”的最终门禁；exit code 便于 CI/脚本串联。
- **Alternatives**: 复用 `evaluation/evaluate.py`（依赖项目环境、且其定位是评分而非打包校验）；只用 `pytest`（不覆盖 zip/提交目录）。
- **Consequences**: 与 `evaluate.py` 的契约检查有重叠（有意的双保险）；两者发现不一致时以题面为准并记录在 tasklog。

### D18 — README 用英文；内部 planning 文档不进包
- **Status**: accepted（2026-10-25）
- **Decision**: `README.md` 与 `INTERVIEW_GUIDE.md` 用英文（评委/面试需要）；`docs/planning/*` 保留中文工作记录，排除出 `code.zip`。
- **Rationale**: 题面要求 README 说明清楚、供评委复现；内部讨论语言不影响评审，但不应打包。
- **Alternatives**: README 中文（评委可能无法阅读）；planning 打包（含未核实事项与内部讨论，非交付物）。
- **Consequences**: 英文文档中的度量数字必须来自最终真实运行，不用占位符冒充。

### D19 — pyproject 项目名改为 `ghost-audit`（模块 `ghost_audit`）
- **Status**: accepted（2026-10-25，Lead 确认）
- **Decision**: `pyproject.toml` 的 project name 从模板名 `templete-project` 改为 `ghost-audit`，使 `uv sync` 后 `uv run python -m ghost_audit` 可用；模板残留 `src/templete_project/` 与 `tests/test_main.py` 由 Lead 删除。
- **Rationale**: README 与评估 harness 都以 `python -m ghost_audit` 为入口（Lead 确认的 CLI 合同）。
- **Alternatives**: 保留模板名并依赖 `PYTHONPATH=src`（与 README/评估器合同不符，且打包后更脆弱）。
- **Consequences**: 打包脚本对模板残留 `src/templete_project/` 给出警告；`src/*/config/` 密钥目录始终排除。

### D20 — 校验与构建脚本不进入 git 之外的分发
- **Status**: accepted（2026-10-25）
- **Decision**: `scripts/build_code_zip.py` 与 `scripts/validate_submission.py` 随 `code.zip` 一起提交（评委可复核）；私有自测数据放 `work/` 且不提交。
- **Rationale**: 可复现的打包/校验流程增强可信度，成本几乎为零。
- **Alternatives**: 只提交运行时代码（评委无法复核交付物）；把自测脚本也放进 tests（其依赖官方 dataset，跨平台不可靠）。
- **Consequences**: 两个脚本需保持 stdlib-only 与路径无关；`work/` 已 gitignore。

### D21 — 行排序采用“数值 case 序号”，不是字典序
- **Status**: accepted（2026-10-25，Lead 确认）
- **Decision**: `output.csv` 的行按 case 编号数值升序：`case_33, case_99, case_100, …, case_550`；把 `case_100` 排在 `case_33` 之前（字典序）视为**错误**。`scripts/validate_submission.py` 的行序检查、README、提交清单均按此实现/表述。
- **Rationale**: Lead 确认官方 canonical 答案使用数值顺序；样例集 case_01–case_32 无法区分两种排序，故必须显式规定。Lead 已相应修改 pipeline 输出顺序。
- **Alternatives**: 字典序（`sorted(case_id)`，Python 默认）——与 canonical 不一致；按 `deletion_requests.csv` 原文件顺序——与题面“sorted by case_id”不符。
- **Consequences**: 校验脚本的排序检查改为 `case_sort_key()`（数值 key）；README/清单明确写出示例；旧版 output.csv（字典序）会被校验直接报错。

### D22 — `code.zip` 打包 intent cache、排除本地 telemetry 与临时目录
- **Status**: accepted（2026-10-25，Lead 确认）
- **Decision**: 打包 `evaluation/intent_cache.json`（LLM 复核缓存：仅请求 hash + 标签，不含请求原文/密钥），使 `--llm-intent` 重跑可离线复现；排除 `evaluation/llm_usage.jsonl`（本地 telemetry，干净数字写入 usage_report.md）、`evaluation/.tmp/**`、`.ocr-cache/`、`work/`。`output.csv`/`log.txt`/`submission/` 始终不在 code.zip 内（作为单独提交物）。
- **Rationale**: 复现性与评审要求平衡：cache 是复现输入的一部分，telemetry 是过程数据且可能含运行细节。
- **Alternatives**: cache 与 telemetry 都不打包（`--llm-intent` 重跑需重新调用模型，不可离线复现）；全部打包（telemetry 与临时数据不属于交付内容）。
- **Consequences**: `build_code_zip.py` 的排除清单新增 `llm_usage.jsonl`、`evaluation/.tmp/`；README 与提交清单同步说明。

---

## 待决定 / 待核实（非 blocked，记录在此防止遗忘）

| # | 问题 | 现状 | 决策方式 |
| --- | --- | --- | --- |
| O1 | hidden canonical 精确内容 | 未核实（只有 32 样例有标注） | 以合同正确性 + 样例回归为目标，不宣称 hidden 准确率 |
| O2 | 匿名 analytics 的 user 归属 | 未核实（快照排序 + 时间窗 + 消除法近似） | 评估报告中披露为已知不确定点 |
| O3 | 评分权重细节 | 未核实（题面只列维度） | 不臆测权重，按合同/样例最优化 |
| O4 | 官方 deadline | 未配置 | 按参考 AGENTS：不虚构截止时间 |
| O5 | `--llm-intent` 对最终 output 的实际影响 | 待最终运行验证 | Lead 在最终运行确认；报告记录 LLM 是否改变任何 case |
| O6 | evaluation_report/usage_report 的实测数字 | 待最终全量运行 | eval-harness/Lead 提供数据后由 docs-packaging 定稿 |
