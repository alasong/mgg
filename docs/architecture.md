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
cmd_run
  ├── _infer_skill(prompt)            → 路由选择
  ├── _build_claude_args(prompt, skill)→ 参数构建
  ├── subprocess.run(args)             → 子进程 (batch)
  ├── _run_interactive_loop(prompt,skill)→ 子进程 (interactive)
  │   ├── _run_claude_with_session()   → 会话子进程
  │   │   ├── _build_claude_args()     → 参数构建（含 session）
  │   │   └── _parse_claude_output()   → 输出解析
  │   ├── _extract_decision_from_output() → 决策提取
  │   │   ├── _validate_decision_json()   → 校验
  │   │   └── _extract_markdown_decision_table() → 表格解析
  │   ├── _prompt_human_for_decision() → 用户输入
  │   └── _find_choice_label()         → 标签查找
  ├── _parse_claude_output()           → 输出解析 (batch)
  ├── _wait_dependencies()             → 依赖等待
  ├── _extract_decision_from_output()  → 事后决策 (batch only)
  │   └── _save_decision()             → 决策持久化
  ├── _save_task()                     → 任务持久化
  └── _print_status_line()             → 状态输出

cmd_status
  ├── _load_task()                     → 任务加载
  └── _print_status_line()             → 状态输出

cmd_ls
  └── _discover_skills()               → Skill 发现
      └── _parse_skill_meta()          → 元数据解析

cmd_resume
  └── cmd_run (re-entry)               → 重跑

cmd_decide
  ├── _load_task()                     → 任务加载
  ├── _extract_decision_from_output()  → 决策提取
  └── _save_decision()                 → 决策保存
```

## 数据流

### batch 模式
```
用户输入 (prompt)
  → argparse 解析 → cmd_run
    → _infer_skill (路由)
    → _build_claude_args (参数构建)
    → subprocess.run → claude 子进程
    → _parse_claude_output (NDJSON 解析)
    → _extract_decision_from_output (事后决策)
    → _save_task / _save_decision (持久化)
    → _print_status_line (输出)
```

### interactive 模式
```
用户输入 (prompt + -i)
  → argparse 解析 → cmd_run
    → _run_interactive_loop
      → Round 1: _run_claude_with_session
      → Round 1-N:
        决策? → _prompt_human_for_decision → 用户输入
              → _run_claude_with_session(choice)
        无决策 → 结束
    → _save_task (持久化)
    → _print_status_line (输出)
```

## 模块边界

| 模块 | 文件 | 函数数 | 对外接口 | 职责 |
|------|------|--------|---------|------|
| CLI 入口 | mgg.py | 5 (cmd_*) | `mgg run/status/ls/resume/decide` | 命令解析、参数校验 |
| Skill 路由 | mgg.py | 1 | `_infer_skill()` | 提示词 → Skill 匹配 |
| 出解析 | mgg.py | 1 | `_parse_claude_output()` | NDJSON → dict |
| 决策通道 | mgg.py | 7 | `_extract/validate/save/load/find/inject/prompt` | 决策提取、校验、持久化、注入 |
| 交互循环 | mgg.py | 2 | `_run_interactive_loop/with_session` | 多轮会话决策 |
| 持久化 | mgg.py | 2 | `_save_task/_load_task` | JSON 文件读写 |
| 工具函数 | mgg.py | 6 | `die/_now/_discover_skills/_parse_skill_meta/_wait_dependencies/_print_status_line` | 通用辅助 |
