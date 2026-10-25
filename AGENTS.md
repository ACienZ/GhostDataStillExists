# AGENTS.md — Ghost Data Still Exists (local working rules)

本文件是本期 HackerRank Orchestrate「Ghost Data Still Exists」交付项目的本地工作规则。
若与 `~/.dsh/AGENTS.md` 冲突，以 `~/.dsh/AGENTS.md` 为准；若与用户提示词冲突，以用户提示词为准。

## 0. 项目定位

- 目标仓库：https://github.com/ACienZ/GhostDataStillExists
- 题目：https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists
- 只读参考仓库：`docs/refs/hackerrank-orchestrate-october26-main/`（**不要修改，不要提交**）。
  其中 `AGENTS.md`、`README.md`、`problem_statement.md`、`dataset/` 是题意与官方样例来源。
- 交付物目录：`submission/`（output.csv、code.zip、log.txt、INTERVIEW_GUIDE.md）。
- 工作日志：仓库根目录 `log.txt`，最终复制为 `submission/log.txt`。只追加、不重写；不记录任何密钥。

## 1. 环境

- Python 版本见 `.python-version`（3.13），依赖用 **uv** 安装到项目 `.venv`。
- 本机沙箱不允许写 `~/.cache/uv`，因此所有 uv 命令必须带项目内缓存目录：

  ```bash
  export UV_CACHE_DIR="$PWD/.uv-cache"
  uv sync
  uv run pytest
  ```

- 运行完整流程（需要官方 dataset，位于只读参考目录中）：

  ```bash
  uv run python -m ghost_audit run \
    --dataset docs/refs/hackerrank-orchestrate-october26-main/dataset \
    --output output.csv
  ```

- 图片证据（PNG）需要 OCR：本机使用 `scripts/ocr_images.swift`（macOS Vision）。OCR 结果缓存于 `work/ocr/`，不进入交付包。

## 2. 关键约束（来自题目）

- 只允许使用 `dataset/` 下的 participant-facing 文件；不得使用任何 organizer-only 真值。
- 不得修改官方样例答案或输入数据来让测试通过。
- 只使用 `audit_at` 之前（`captured_at <= audit_at`）的证据决定案例状态；晚于 `audit_at` 的 evidence 只能作为静态身份关联的旁证，并须在设计文档中记录。
- `reported_status`、活动 `reported_result` 都只是 claim，不能作为完成证明。
- 最终 `output.csv` 必须恰好 518 行数据，按 `case_id` 排序；`steps_json` 是有序 JSON 数组，step_no 从 1 连续递增。
- 交付包中不得包含 dataset、`.venv`、缓存、嵌套压缩包、API key、凭据。

## 3. Git / GitHub 流程

- Feature Branch：一个 issue 一个分支；commit message 英文，结尾包含 `Co-authored-by: DSH-Team <noreply@deepseek.com>`。
- 每个分支完成后开 PR、自审、等 CI 通过再 squash merge。
- GitHub 写入只允许：目标仓库 issues/PR/branches/Project（"GhostDataStillExists Tracker"）、以及本仓库内容。

## 4. 验收标准

1. `uv run pytest` 全部通过（依赖 dataset 的用例在 dataset 缺失时 skip）。
2. `output.csv` 通过契约校验与官方样例回归（样例集指标记录在 `evaluation/evaluation_report.md`）。
3. `code.zip` 解压到干净目录后按 README 可复现。
4. `log.txt` 符合参考仓库 `AGENTS.md` §5 的格式（`tool=`、`model=` 必填）。
5. 所有未核实事项记录在 `docs/planning/` 中。
