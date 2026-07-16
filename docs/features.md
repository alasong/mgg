# mgg 功能点梳理

## CLI 命令

| 命令 | 功能 | 参数 | 说明 |
|------|------|------|------|
| `mgg run <prompt...>` | 执行新任务 | `--skill/-s`, `--no-skill`, `--dep`, `--inject`, `--interactive/-i`, `--parallel`, `--max-workers` | 派发 Claude Code 子进程，支持单任务或并行多任务 |
| `mgg status [task_id]` | 查看任务状态 | 可选 task_id | 无 id 列出所有，有 id 显示详情 |
| `mgg ls` | 列出可用 Skill | 无 | 扫描 `~/.claude/skills/` |
| `mgg resume <task_id>` | 重跑失败任务 | task_id | 用相同 prompt 重新执行 |
| `mgg decide <task_id> <choice>` | 为任务记录决策 | task_id, choice | 非交互式记录决策 |

## 并行执行（迭代4 新增）

| 功能 | 说明 |
|------|------|
| `mgg run p1 p2 p3 --parallel` | 同时执行多个 prompt，每个独立子进程 |
| `--max-workers N` | 控制最大并发数（默认 3） |
| 错误隔离 | 单任务失败不影响其他任务 |
| 独立持久化 | 每个任务独立保存 state.json + result.md |
| Skill 推理 | 使用第一个 prompt 推理 skill，所有任务共享 |

## Skill 路由

- **自动路由**：根据 prompt 关键词匹配合适的 skill
- **路由规则**：
  - `审查/review/audit` → `paa`（双 Agent 审查）
  - `并行/parallel/多个` → `pdu`（并行执行）
  - `tdd/测试驱动` → `ulw`（TDD 执行）
  - `流程/多步/pipeline` → `pfs`（流程编排）
  - `分析/research/调研` → `pff`（因子分析）
  - 默认 → `pdu`（并行执行）
- **手动指定**：`mgg run --skill <name>` 跳过推理
- **跳过路由**：`mgg run --no-skill` 直接执行

## 决策通道

| 模式 | 命令 | 决策时机 | 交互方式 |
|------|------|---------|---------|
| 事后决策 | `mgg run` | 子进程完成后 | 解析 stdout 中的决策结构体，提示用户 |
| 实时交互 | `mgg run -i` | 每轮执行后 | session 保持上下文，多轮询问 |
| 非交互注入 | `mgg decide` + `--inject` | 跨任务 | 读取前序决策并注入到新任务 |

**决策结构体格式**（由 Claude 在输出中生成）：
- **JSON 代码块**：````json `{"question":"...","options":[{"id":"A","label":"...","pros":"...","cons":"..."}]}` ````
- **Markdown 表格**：`| 方案 | 优点 | 缺点 |` 格式

## 任务依赖编排

- `mgg run --dep TASK_A TASK_B --inject TASK_C`
- **`--dep`**：等待依赖任务完成后才开始
- **`--inject`**：将前序任务的决策结果注入 prompt
- **结合使用**：可构建多步骤管道

## 任务状态管理

- **状态机**：`running` → `done` / `failed`
- **持久化**：`.mgg/tasks/<id>/state.json`
- **结果存储**：`.mgg/tasks/<id>/result.md`
- **决策记录**：`.mgg/tasks/<id>/decision.json`
- **状态查看**：`mgg status [task_id]`

## 交互模式（迭代2 新增）

- `mgg run --interactive` / `mgg run -i`
- Claude 子进程使用 session 保持上下文
- 检测到决策点时暂停，等待用户选择
- 选择后继续执行，最多 5 轮决策
- 所有轮次结果合并为最终输出

## 测试覆盖

- 123 个测试用例，整体覆盖率 91%
- 核心模块覆盖率：决策 98%、路由 100%、持久化 100%、常量 100%
- 覆盖：决策通道解析、预分析决策、输出解析、Skill 路由、任务状态、交互循环、CLI 命令、并行调度、依赖等待、人工提示、argparse

## 预分析决策（Preflight，迭代5 新增）

`mgg run` 默认在**执行主任务前**先做轻量预分析：

1. **分析** — Claude 子进程对 prompt 做轻量分析，列出需要你确认的决策点（数据库选择、认证方式等）
2. **确认** — 批量展示所有决策点，你逐个选择或跳过
3. **注入** — 将已确认的决策以 `[已确认决策]` 结构体注入主 prompt，Claude 直接按决策执行
4. **兜底** — 执行中 Claude 产出了未预料到的决策，走事后追问机制，不丢

```
mgg run "实现登录模块"
  → 预分析: 检测到 2 个决策点
    1. 数据库: [Postgres/SQLite] → 选 Postgres
    2. 认证: [JWT/Session] → 选 JWT
  → 注入决策 → 执行主任务（不再中断）
  → 若 Claude 输出意外决策 → 事后追问
```

| 参数 | 说明 |
|------|------|
| `--no-preflight` | 跳过预分析，直接执行（行为等同于迭代4）|

## 规划中

| 功能 | 迭代 | 说明 |
|------|------|------|
| — | — | 暂无 |
