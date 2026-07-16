# mgg 使用文档

## 安装

```bash
# mgg 是单文件 Python CLI，无需安装
alias mgg='python3 /path/to/mgg/mgg.py'
```

依赖：Python ≥ 3.10 + [Claude Code CLI](https://claude.ai/code)（`claude` 命令需在 PATH 中可用）。

## 基础使用

### 运行任务

```bash
mgg run "写一个 Python 函数实现 Fibonacci"
```

mgg 会自动根据 prompt 关键词路由到最合适的 Skill（pdu/paa/ulw/pfs/pff），然后派发 Claude Code 子进程执行。

### 指定 Skill

```bash
mgg run --skill paa "审查这段代码"    # 强制用审查 skill
mgg run --no-skill "直接执行这个命令"  # 不走 skill 路由
```

### 查看状态

```bash
mgg status                  # 列出所有任务
mgg status <task_id>        # 查看特定任务详情 + 结果摘要
```

### 列出可用 Skill

```bash
mgg ls
```

### 重跑失败任务

```bash
mgg resume <task_id>
```

## 高级使用

### 交互模式（决策通道）

遇到需要人工判断的场景，mgg 可以暂停等待输入：

```bash
mgg run -i "设计 API 认证方案"
```

Claude 执行过程中输出决策结构体（JSON 代码块或 Markdown 表格），mgg 暂停并展示：

```
┌──────────────────────────────────────────┐
│ 问题: 选择认证方案                        │
│                                          │
│ A: JWT Token   无状态，适合分布式         │
│ B: Session     传统，适合单体             │
│ C: OAuth2      标准协议，第三方集成        │
│                                          │
│ 输入选项 ID (或留空跳过): A               │
└──────────────────────────────────────────┘
```

选择后 Claude 继续，保持上下文，最多可交互 5 轮。

### 任务依赖编排

```bash
# 先跑依赖任务
mgg run "设计数据模型" --dep task_a task_b
```

### 决策注入

将一个任务的决策结果注入到另一个任务：

```bash
mgg run "task_a 的分析"                    # 产生决策
mgg run "基于前序决策实现" --inject task_a  # 注入决策
```

### 组合：依赖 + 注入

```bash
mgg run "调研方案"               # → task_a
mgg run "实现" --dep task_a --inject task_a  # 等调研完再实现
```

### 非交互式决策记录

```bash
mgg decide <task_id> <choice>   # 为已完成任务记录决策
```

## 任务管理

所有任务数据存储在项目根目录的 `.mgg/tasks/`：

```
.mgg/tasks/<task_id>/
├── state.json       # 状态（JSON）：id, prompt, skill, status, cost...
├── result.md        # 执行结果（文本）
└── decision.json    # 决策记录（可选）
```

## 决策结构体格式

Claude 在输出中可以通过以下格式抛出决策点供用户选择：

### 方式 1：JSON 代码块

````
```json
{
  "question": "选哪个方案？",
  "options": [
    {"id": "A", "label": "方案A", "pros": "优点", "cons": "缺点"},
    {"id": "B", "label": "方案B", "pros": "优点", "cons": "缺点"}
  ]
}
```
````

### 方式 2：Markdown 表格

```
## 决策点

问题：选哪个方案？

| 方案 | 优点 | 缺点 |
|------|------|------|
| A: 方案A | 优点 | 缺点 |
| B: 方案B | 优点 | 缺点 |
```

## 常见场景

### 代码审查

```bash
mgg run --skill paa "审查 src/auth.py 的认证逻辑"
```

### 并行开发

```bash
mgg run "并行实现用户 CRUD 和数据校验"
```

### 技术调研

```bash
mgg run "分析三种缓存方案的优缺点"
```

### TDD 实现

```bash
mgg run "用 TDD 实现一个 LRU Cache"
```

## 测试

```bash
python3 -m pytest tests/ -n auto -q   # 并行运行所有测试
```
