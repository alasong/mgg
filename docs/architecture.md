# mgg 架构文档

## 分层架构

```
┌───────────────────────────────────────────────────────────┐
│                   CLI 层 (cmd_*)                           │
│                                                           │
│  cmd_run      cmd_status    cmd_ls    cmd_resume  cmd_decide│
│  ┌─────────┐  ┌──────────┐  ┌──────┐  ┌─────────┐  ┌────┐ │
│  │ argparse│  │ 状态展示  │  │skill │  │重跑任务  │  │决策 │ │
│  │ 参数解析 │  │ 列表/详情│  │列表  │  │        │  │记录 │ │
│  └─────────┘  └──────────┘  └──────┘  └─────────┘  └────┘ │
└──────────────────────────┬────────────────────────────────┘
                           │ 调用
┌──────────────────────────▼────────────────────────────────┐
│                   调度层 (Orchestrator)                     │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Skill 路由    │  │ 决策通道     │  │ 依赖编排          │ │
│  │ _infer_skill │  │ extract     │  │ _wait_dependencies│ │
│  │ → paa/pdu/.. │  │ → prompt    │  │ → dep 等待       │ │
│  └──────────────┘  │ → save      │  └──────────────────┘ │
│                    │ → inject    │                        │
│                    └──────┬───────┘                       │
└───────────────────────────┼──────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│                   执行层 (Execution)                       │
│                                                           │
│  ┌──────────────────────┐  ┌───────────────────────────┐  │
│  │ 子进程管理            │  │ 输出解析                   │  │
│  │ _build_claude_args   │  │ _parse_claude_output      │  │
│  │ _run_claude_with_    │  │ NDJSON → text + cost + id │  │
│  │   session            │  └───────────────────────────┘  │
│  │ _run_interactive_loop│                                 │
│  │ subprocess.run       │                                 │
│  └──────────────────────┘                                 │
└───────────────────────────┬──────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│                   持久层 (Persistence)                     │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ state.json   │  │ result.md    │  │ decision.json    │ │
│  │ _save_task   │  │ 执行结果     │  │ _save_decision   │ │
│  │ _load_task   │  │ 文本存储     │  │ _load_decision   │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

## 函数依赖图

```
cmd_run (cli.py)
  ├── _infer_skill(prompt)            → 路由选择 (router.py)
  ├── [默认] _preflight_analyze       → 预分析决策点 (analyzer.py)
  │   └── subprocess.run → claude -p  → 轻量子进程
  ├── _batch_prompt_human             → 批量确认 (analyzer.py)
  ├── _build_injection_text           → 注入 prompt (analyzer.py)
  ├── _build_claude_args(prompt, skill)→ 参数构建 (executor.py)
  ├── subprocess.run(args)             → 子进程 (batch) (executor.py)
  ├── _run_interactive_loop(prompt,skill)→ 子进程 (interactive) (executor.py)
  │   ├── _run_claude_with_session()   → 会话子进程
  │   │   ├── _build_claude_args()     → 参数构建（含 session）
  │   │   └── _parse_claude_output()   → 输出解析
  │   ├── _extract_decision_from_output() → 决策提取 (decision.py)
  │   │   ├── _validate_decision_json()   → 校验
  │   │   └── _extract_markdown_decision_table() → 表格解析
  │   ├── _prompt_human_for_decision() → 用户输入 (decision.py)
  │   └── _find_choice_label()         → 标签查找 (decision.py)
  ├── _parse_claude_output()           → 输出解析 (batch) (executor.py)
  ├── _wait_dependencies()             → 依赖等待 (utils.py)
  ├── _extract_decision_from_output()  → 事后决策兜底 (batch only) (decision.py)
  │   └── _save_decision()             → 决策持久化 (persistence.py)
  ├── _save_task()                     → 任务持久化 (persistence.py)
  └── _print_status_line()             → 状态输出 (utils.py)

cmd_status (cli.py)
  ├── _load_task()                     → 任务加载 (persistence.py)
  └── _print_status_line()             → 状态输出 (utils.py)

cmd_ls (cli.py)
  └── _discover_skills()               → Skill 发现 (router.py)
      └── _parse_skill_meta()          → 元数据解析 (router.py)

cmd_resume (cli.py)
  └── cmd_run (re-entry)               → 重跑

cmd_decide (cli.py)
  ├── _load_task()                     → 任务加载 (persistence.py)
  ├── _extract_decision_from_output()  → 决策提取 (decision.py)
  └── _save_decision()                 → 决策保存 (persistence.py)
```

## 数据流

### batch 模式（含 Preflight）
```
用户输入 (prompt)
  → argparse 解析 → cmd_run (cli.py)
    → _infer_skill (路由) (router.py)
    → [默认] _preflight_analyze → 分析决策点 (analyzer.py)
      → _batch_prompt_human → 批量确认 (analyzer.py)
      → _build_injection_text → 注入 prompt (analyzer.py)
    → _build_claude_args (参数构建) (executor.py)
    → subprocess.run → claude 子进程 (executor.py)
    → _parse_claude_output (NDJSON 解析) (executor.py)
    → _extract_decision_from_output (事后决策兜底) (decision.py)
    → _save_task / _save_decision (持久化) (persistence.py)
    → _print_status_line (输出) (utils.py)

  --no-preflight: 跳过预分析，直接执行
```

### interactive 模式
```
用户输入 (prompt + -i)
  → argparse 解析 → cmd_run (cli.py)
    → _run_interactive_loop (executor.py)
      → Round 1: _run_claude_with_session
      → Round 1-N:
        决策? → _prompt_human_for_decision → 用户输入 (decision.py)
              → _run_claude_with_session(choice) (executor.py)
        无决策 → 结束
    → _save_task (持久化) (persistence.py)
    → _print_status_line (输出) (utils.py)
```

### parallel 模式
```
用户输入 (prompts [p1, p2, ...])
  → argparse 解析 → cmd_run (cli.py)
    → _run_tasks_parallel (executor.py)
      → ThreadPoolExecutor (max_workers)
        → _run_single_task(p1)   ─┐
        → _run_single_task(p2)   ─┤ 独立子进程，错误隔离
        → _run_single_task(pN)   ─┘
    → 结果汇总 → _print_status_line (utils.py)
```

## 模块边界

| 模块 | 文件 | 函数数 | 对外接口 | 职责 |
|------|------|--------|---------|------|
| CLI 入口 | `cli.py` | 5 (cmd_*) + main | `mgg run/status/ls/resume/decide` | 命令解析、参数校验、输出格式化 |
| Skill 路由 | `router.py` | 2 | `_infer_skill()` | 提示词 → Skill 匹配 |
| 执行器 | `executor.py` | 6 | `_run_single_task()` / `_run_tasks_parallel()` | 子进程管理、并行调度、输出解析 |
| 决策通道 | `decision.py` | 7 | `_extract/validate/save/load/find/inject/prompt` | 决策提取（JSON/表格）、校验、人工提示、注入 |
| 持久化 | `persistence.py` | 4 | `_save_task/_load_task/_save_decision/_load_decision` | JSON 文件读写 |
| 工具函数 | `utils.py` | 3 | `_wait_dependencies/_print_status_line/_now` | 依赖等待、状态输出、时间工具 |
| 常量 | `constants.py` | 0 | `MGG_DIR/TASKS_DIR/SKILLS_DIR` | 纯路径常量（无内部依赖的叶子模块） |
| 入口 | `__init__.py` + `__main__.py` | 2 | `from mgg.cli import main` | 包导入 + `python -m mgg` 入口 |
| 预分析 | `analyzer.py` | 3 | `_preflight_analyze/_batch_prompt_human/_build_injection_text` | 执行前轻量 Claude 分析决策点、批量确认、注入 |
