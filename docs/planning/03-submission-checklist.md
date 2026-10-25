# 03 — Submission checklist (official requirements)

提交前逐项勾选。命令在仓库根目录执行，先设置环境：

```bash
cd /Users/acienz/Desktop/GhostDataStillExists
export UV_CACHE_DIR="$PWD/.uv-cache"
DATASET_DIR=docs/refs/hackerrank-orchestrate-october26-main/dataset   # 或 HackerRank 指定路径
```

来源：官方 `problem_statement.md`、参考仓库 `README.md`、`AGENTS.md` §6.8/§6.9。
提交入口：<https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists>

---

## A. 最终产物门禁（一条命令）

```bash
uv run python scripts/validate_submission.py --dataset "$DATASET_DIR" --verbose
```

- [ ] 退出码 `0`，输出 `RESULT: PASS`
- [ ] `output.csv`、`submission/code.zip`、`submission/log.txt`、`submission/INTERVIEW_GUIDE.md` 全部存在
- [ ] `submission/` 中无多余文件（`.DS_Store` 等清理掉）
- [ ] `scripts/validate_submission.py` 与 `evaluation/evaluate.py validate` 均无 ERROR

## B. `output.csv`（HackerRank 单独上传）

- [ ] 文件位于仓库根目录 `output.csv`，并已复制到 `submission/output.csv`
- [ ] header 精确为 `case_id,deletion_status,steps_json`
- [ ] 恰好 **518** 行数据（表头之外），覆盖 `deletion_requests.csv` 全部 case
- [ ] 按 `case_id` **数值升序**排列（`case_33, case_99, case_100, …, case_550`；非字典序），无重复
- [ ] `deletion_status ∈ {COMPLETE, INCOMPLETE, NOT_APPLICABLE}`
- [ ] 每个 `steps_json` 是合法 JSON 数组
- [ ] 每个 step 恰好 7 个字段；`step_no` 从 1 连续
- [ ] (phase, operation, state) 均在允许表中；phase 内顺序符合“操作表顺序 → system_id → resource_id”
- [ ] `NOT_APPLICABLE` → `[]`
- [ ] `COMPLETE` → 仅 VERIFICATION，且引用 `captured_at <= audit_at` 的证据
- [ ] `INCOMPLETE` → FINDING + REMEDIATION + 后续 VERIFICATION；remediation/未来验证 `evidence_id=""`
- [ ] 抽查：无引用 `captured_at > audit_at` 的证据；无引用不存在的 evidence id
- [ ] 文件编码 UTF-8，无 BOM 依赖（validator 兼容 BOM）

复核命令：

```bash
uv run python scripts/validate_submission.py --dataset "$DATASET_DIR"
uv run python evaluation/evaluate.py validate \
  --output output.csv \
  --requests "$DATASET_DIR/deletion_requests.csv" \
  --dataset "$DATASET_DIR"
```

## C. `submission/code.zip`（HackerRank 单独上传 code.zip）

- [ ] 由 `uv run python scripts/build_code_zip.py` 生成（确定性、打印 SHA-256）
- [ ] 包含 `README.md`（英文，含 setup/run 命令）
- [ ] 包含 `evaluation/evaluation_report.md`
- [ ] 包含 `evaluation/usage_report.md`
- [ ] 包含可运行入口 `src/ghost_audit/__main__.py`（`uv run python -m ghost_audit run ...`）
- [ ] 包含 `pyproject.toml`、`uv.lock`、`.python-version`、`src/**`、`tests/**`、`evaluation/**`、`scripts/**`
- [ ] 包含 `evaluation/intent_cache.json`（hashes+labels，支持 `--llm-intent` 离线复现）
- [ ] **不含** `evaluation/llm_usage.jsonl`（本地 telemetry）与 `evaluation/.tmp/**`
- [ ] **不含** `dataset/` 及任何官方数据文件（`deletion_requests.csv`、`sample_output.csv`、`evidence/` 等）
- [ ] **不含** `.venv`、`.git`、`.uv-cache`、`.ocr-cache`、`__pycache__`、`.pytest_cache`、`work/`
- [ ] **不含** 嵌套压缩包（`.zip/.tar/.gz/.tgz/.7z/.rar/.whl`）
- [ ] **不含** API key/凭据/私钥；无 `.env`、`api_key.txt`、`src/*/config/`
- [ ] **不含** `output.csv`、`log.txt`、`submission/`（它们是单独提交物）
- [ ] 解压到干净目录后按 README 可复现（见 F 节）

复核命令：

```bash
uv run python scripts/build_code_zip.py --dry-run --list   # 人类可读清单
uv run python scripts/build_code_zip.py                     # 生成 submission/code.zip
unzip -l submission/code.zip | head -40
uv run python scripts/validate_submission.py --dataset "$DATASET_DIR"
```

## D. `log.txt` → chat_transcript（HackerRank 单独上传）

- [ ] 仓库根 `log.txt` 是**追加式** agent 会话记录（Lead 维护，不重写历史）
- [ ] 每个条目含 `tool=` 与 `model=` 行（参考 AGENTS.md §5 要求；最终多为 `tool=DeepSeek Harness`、`model=deepseek-flash`）
- [ ] 无 API key、token、cookie、私钥、真实个人数据
- [ ] 已复制为 `submission/log.txt`
- [ ] HackerRank 上该文件上传到 **chat_transcript** 槽位（不是 code.zip 内）

复核命令：

```bash
grep -c 'tool=' log.txt && grep -c 'model=' log.txt
grep -nE 'sk-[A-Za-z0-9]{16,}|-----BEGIN .*PRIVATE KEY-----|Bearer [A-Za-z0-9._-]{20,}' log.txt || echo "no secrets found"
diff -q log.txt submission/log.txt && echo "log copies identical"
```

## E. 评估与用量报告（必须在 `code.zip` 内）

- [ ] `evaluation/evaluation_report.md` 含：
  - [ ] case-level deletion-status accuracy
  - [ ] step-level 与 field-level accuracy
  - [ ] sequence accuracy
  - [ ] **≥3 个团队自建评估案例**（case 数据 + 手写 expected + 理由）
  - [ ] failures found and improvements made
- [ ] `evaluation/usage_report.md` 含（针对产出最终 `output.csv` 的全量运行）：
  - [ ] model provider(s) 与 model name(s)
  - [ ] model call 次数
  - [ ] input / output tokens
  - [ ] total 与 average tokens per request
  - [ ] estimated total 与 per-request cost（单位 USD，注明价格假设）
  - [ ] 若多模型：分模型 + 总体合计
- [ ] 两份报告中的数字来自**真实最终运行**（不用占位/编造；`TBD` 清空）
- [ ] 报告中不含 key/凭据/敏感配置

复核命令：

```bash
grep -n "TBD\|TODO" evaluation/evaluation_report.md evaluation/usage_report.md || echo "no placeholders"
unzip -p submission/code.zip evaluation/evaluation_report.md | head -20
unzip -p submission/code.zip evaluation/usage_report.md | head -20
```

## F. 干净目录复现（code.zip 可运行性）

- [ ] 解压到空目录，仅输入 `code.zip` + 官方 dataset，按 README 可跑通
- [ ] 复现出的 `output.csv` 与提交的 `output.csv` 内容一致（或差异有解释并记录）
- [ ] 无对本机绝对路径的依赖（`docs/refs/...` 只是本地参考，不作为默认必需路径）
- [ ] 无 API key 时（`--no-llm` 或默认）仍能产出完整 518 行

```bash
rm -rf /tmp/ghost-clean && mkdir -p /tmp/ghost-clean
cd /tmp/ghost-clean
unzip /Users/acienz/Desktop/GhostDataStillExists/submission/code.zip
export UV_CACHE_DIR="$PWD/.uv-cache"
uv sync
uv run pytest -q
uv run python -m ghost_audit run --dataset "$DATASET_DIR" --output output.csv
uv run python scripts/validate_submission.py --csv output.csv --skip-missing --verbose
# 与提交文件对比（允许排序/换行差异时用 diff，严格一致时用 cmp）：
diff <(sort output.csv) <(sort /Users/acienz/Desktop/GhostDataStillExists/output.csv) && echo "reproduced identically"
```

## G. AI interview 准备（INTERVIEW_GUIDE.md）

- [ ] `submission/INTERVIEW_GUIDE.md` 已完成（无 `TODO` 占位）
- [ ] 覆盖：问题理解、架构、证据处理/身份链接/时点重建、确定性 vs 模型分工、测试与评估、失败与改进、成本与已知限制
- [ ] 含基于最终运行数据的 Q&A（数字与 `evaluation_report.md`/`usage_report.md` 一致）
- [ ] 与本次提交的代码/输出一致（无未实现功能描述）

复核命令：

```bash
grep -c "TODO" submission/INTERVIEW_GUIDE.md || echo "no TODOs"
uv run python scripts/validate_submission.py --dataset "$DATASET_DIR"   # 含 TODO/密钥检查
```

## H. 最终 HackerRank 提交映射

| HackerRank 槽位 | 本地文件 | 备注 |
| --- | --- | --- |
| `output.csv` | `submission/output.csv` | 518 行、排序、合同通过 |
| `code.zip` | `submission/code.zip` | 含 README + evaluation 报告，无 dataset/密钥 |
| `chat_transcript` | `submission/log.txt` | 根 `log.txt` 的副本 |
| AI interview | `submission/INTERVIEW_GUIDE.md` | 现场讲解准备材料 |

- [ ] 提交前最后一刻再跑一次 A 节门禁命令并保存输出到 tasklog
- [ ] 提交链接（如需）：<https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists>
- [ ] 不提交 `docs/`、`work/`、`.venv/`、`.uv-cache/`、任何密钥

## I. 已知风险与披露（不阻塞提交，但面试需说明）

- [ ] hidden canonical 不可得：样例回归 ≠ hidden 准确率承诺
- [ ] 匿名 analytics 归属为启发式（快照排序/时间窗/消除法）
- [ ] `--skip-images` 时 PNG 事实缺失，准确率下降，已披露
- [ ] `--llm-intent` 为可选层；最终运行的 LLM 实际影响已记录
- [ ] 官方 deadline 未配置，不虚构
