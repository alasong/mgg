# 迭代4 Spec — 模块化 + 并行调度 + 测试补齐

## 元信息
- **Spec名称**: 迭代4 Spec
- **类型**: 迭代
- **版本**: 1.0.0
- **前置条件**: 迭代3 完成（CLI 集成测试覆盖，覆盖率 83%）
- **输出产物**: 模块化 mgg 包 + 异步并行调度 + 测试覆盖率 ≥ 90%
- **质量标准**: 全部测试通过，覆盖率 ≥ 90%，并行调度功能通过集成测试
- **执行状态文件**: `docs/execution/iteration-4-status.md`

## 依赖Skill
- mgg 开发 Skill (`docs/skills/mgg-dev-skill.md`)

## PDCA执行步骤

### Plan (规划)

**目标**: 将 mgg 从单文件重构为模块化包结构，新增异步并行调度能力，补齐测试覆盖。

#### 架构变更

**模块拆分方案**：

```
mgg/                        # 包目录（mgg.py → mgg/）
├── __init__.py             # 导出 + version
├── __main__.py             # main() 入口
├── cli.py                  # cmd_run / cmd_status / cmd_ls / cmd_resume / cmd_decide
├── router.py               # _infer_skill / _discover_skills / _parse_skill_meta
├── decision.py             # 决策通道（extract / validate / prompt / save / inject / markdown table）
├── executor.py             # Claude 子进程管理 + 异步并行调度
├── persistence.py          # _save_task / _load_task / _save_decision / _load_decision
└── utils.py                # _now / die / _wait_dependencies / _print_status_line
```

**并行调度设计**：

```
mgg run --parallel "prompt1" "prompt2" "prompt3"
  → concurrent.futures.ThreadPoolExecutor(max_workers=3)
    → 每个任务独立 subprocess.run（隔离的 task_id）
    → 各自持久化 state.json + result.md
    → 全部完成后汇总输出
```

**关键约束**：
- 模块拆分 = 纯搬移，接口保持兼容，不改变行为
- 现有 82 个测试在重构后全部通过（import 路径映射正确）
- 并行调度新增功能，不影响串行行为

### Do (执行)

每项活动按 TDD 执行（Red → Green → Refactor）。

**A 组：模块化拆分**

| # | 任务 | 内容 | 原函数 |
|---|------|------|--------|
| 1 | 创建 mgg/ 包结构 | 创建目录 + `__init__.py` + `__main__.py` | — |
| 2 | persistence.py | 状态读写 + 决策读写 | `_save_task`, `_load_task`, `_save_decision`, `_load_decision` |
| 3 | utils.py | 通用工具函数 | `_now`, `die`, `_wait_dependencies`, `_print_status_line` |
| 4 | router.py | Skill 发现与路由 | `_infer_skill`, `_discover_skills`, `_parse_skill_meta` |
| 5 | decision.py | 决策通道 | `_extract_decision_from_output`, `_validate_decision_json`, `_extract_markdown_decision_table`, `_find_choice_label`, `_inject_decision_into_prompt`, `_prompt_human_for_decision` |
| 6 | executor.py | 子进程管理 + 交互循环 | `_build_claude_args`, `_parse_claude_output`, `_run_claude_with_session`, `_run_interactive_loop` |
| 7 | cli.py | CLI 命令入口 | `cmd_run`, `cmd_status`, `cmd_ls`, `cmd_resume`, `cmd_decide` |
| 8 | `__init__.py` | 导出 + argparse parser | 原模块级 `parser` + 各 cmd_* |
| 9 | `__main__.py` | `main()` 入口 | `main()` |
| 10 | mgg.py 保留为桩 | `from mgg.cli import main; main()` 兼容 | 确保 alias 不中断 |

**B 组：异步并行调度**

| # | 任务 | 内容 |
|---|------|------|
| 1 | `executor.py` 新增 `_run_tasks_parallel()` | 接收多个 prompt，ThreadPoolExecutor 并行派发 |
| 2 | `cli.py` `cmd_run` 分支 | 检测 `--parallel` / `--max-workers` 参数，走并行分支 |
| 3 | 并行结果汇总 | 各任务独立持久化，汇总输出状态行列表 |
| 4 | 错误隔离 | 单个任务失败不影响其他任务 |
| 5 | `executor.py` 新增 `_run_tasks_sequential()` | 显式串行执行（默认），重构原 `cmd_run` 逻辑 |

**C 组：测试补齐**

| # | 任务 | 类型 | 预期新增测试数 |
|---|------|------|---------------|
| 1 | `test_prompt_human.py` | stdin mock 覆盖 `_prompt_human_for_decision` | 5 |
| 2 | `test_wait_dependencies.py` | mock time 覆盖 `_wait_dependencies` | 3 |
| 3 | `test_parallel.py` | ThreadPoolExecutor mock 覆盖并行调度 | 6 |
| 4 | 模块化 import 测试 | 验证 `from mgg.* import *` 路径正确 | 2 |

### Check (验证)

**活动**:
1. `python3 -m pytest tests/ -n auto -q` 全部通过（≥ 原有 82 个 + 新增 ≥ 16 个 = ≥ 98 个）
2. 覆盖率 ≥ 90%（`python3 -m pytest tests/ --cov=mgg/`）
3. 并行调度集成测试：3 个并行任务独立持久化、失败隔离
4. 回退测试：`mgg.py` 兼容桩正常工作
5. 现有 batch/interactive 模式行为不变

### Act (改进)

**活动**:
1. 分析未覆盖代码，补充边界测试
2. 更新 AGENT.MD 中的模块边界和函数清单
3. 更新 docs/architecture.md 函数依赖图
4. 记录 TDD 日志

## 变更记录
| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0.0 | 2026-07-16 | 初始版本 | ADE |
