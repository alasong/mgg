# mgg AGENT.MD

> 本文档是 mgg 项目的最高规范，所有开发活动必须遵循本文档定义及 ADE V2.0 开发规范。

## 项目概述

### 项目目标
mgg 是一个 CLI 项目管理工具，通过派发独立的 Claude Code 子进程来执行开发任务，实现自动化开发工作流。

### 核心价值
- 将开发任务自动化派发到 Claude Code，减少人工重复操作
- 通过 Skill 路由系统将任务匹配到最适合的执行单元
- 提供决策通道，在自动化流程中保留人工决策节点
- 支持任务依赖编排，实现复杂工作流

### 技术栈
| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 语言 | Python | >=3.10 | 主开发语言 |
| CLI | Claude Code | latest | 任务执行引擎 |
| 测试框架 | pytest | latest | 单元测试 |
| 测试增强 | pytest-xdist | latest | 并行测试执行 |
| 测试覆盖率 | pytest-cov | latest | 覆盖率统计 |

## 架构规范

### 分层架构
```
┌─────────────────────────────────────┐
│           CLI 层 (Presentation)      │
│  - argparse 命令解析                  │
│  - 用户交互 / 输出格式化              │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│           调度层 (Orchestrator)       │
│  - Skill 路由 / 依赖等待              │
│  - 决策通道 / 任务编排                │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│           执行层 (Execution)          │
│  - Claude Code 子进程管理             │
│  - 输出解析 / 状态追踪               │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│           持久层 (Persistence)        │
│  - .mgg/tasks/ 任务状态 + 结果       │
│  - decision.json 决策记录            │
└─────────────────────────────────────┘
```

### 依赖规则
- **单向依赖**：CLI → 调度层 → 执行层 → 持久层
- **接口隔离**：层间通过函数签名通信
- **模块化**：每个核心功能独立函数，不耦合

### 模块边界
| 模块 | 文件 | 职责 | 对外接口 |
|------|------|------|----------|
| CLI | `cli.py` | 命令解析、参数校验、输出格式化 | `cmd_run`/`cmd_status`/`cmd_ls`/`cmd_resume`/`cmd_decide` |
| Skill 路由 | `router.py` | 根据 prompt 匹配最优 skill | `_infer_skill()` |
| 执行器 | `executor.py` | Claude Code 子进程管理、并行调度 | `_run_single_task()`/`_run_tasks_parallel()` |
| 决策通道 | `decision.py` | 决策提取（JSON/表格）、校验、人工提示 | `_extract_decision_from_output()`/`_prompt_human_for_decision()` |
| 持久化 | `persistence.py` | 任务状态 + 决策 JSON 文件读写 | `_load_task()`/`_save_task()`/`_save_decision()` |
| 工具 | `utils.py` | 依赖等待、状态输出、时间工具 | `_wait_dependencies()`/`_print_status_line()` |
| 常量 | `constants.py` | 路径常量定义 | `MGG_DIR`/`TASKS_DIR`/`SKILLS_DIR` |
| 预分析 | `analyzer.py` | 执行前轻量分析 prompt 估算决策点 | `_preflight_analyze()`/`_batch_prompt_human()`/`_build_injection_text()` |

## 编码规范

### 命名规范
| 类型 | 规则 | 示例 |
|------|------|------|
| 命令函数 | `cmd_*` | `cmd_run`, `cmd_status` |
| 内部函数 | `_` 前缀 | `_infer_skill`, `_parse_claude_output` |
| 常量 | UPPER_SNAKE_CASE | `MGG_DIR`, `TASKS_DIR` |

### 代码风格
- 遵循 PEP 8
- 缩进: 4空格
- 行长度: 100 字符

## 质量标准

### 测试要求
| 指标 | 要求 |
|------|------|
| 核心模块测试覆盖率 | ≥ 80% |
| 决策通道测试覆盖率 | ≥ 90% |

### 代码审查标准
- [ ] 功能逻辑正确
- [ ] 测试覆盖充分
- [ ] 命名清晰
- [ ] 错误处理完善
- [ ] 决策通道有对应测试

## 开发流程

遵循 ADE V2.0 规范的 PDCA 循环：

```
Spec (定义迭代做什么)
  → Skill (定义怎么做)
    → TDD (原子实现)
      → 执行状态文件 (追踪进展)
```

1. **Plan**: 创建/更新 Spec，定义迭代目标和范围
2. **Do**: Spec 引用 Skill → Skill 按 PDCA 执行 → TDD 原子实现
3. **Check**: 运行测试、审查决策通道、验证覆盖率
4. **Act**: 更新复盘、Skill 优化、AGENT.MD 更新

## 文档结构

```
docs/
├── framework/       # 开发规范与模式（方法论 + 实践 + 模板）
├── features.md      # 功能点梳理
├── architecture.md  # 架构文档
├── mechanisms.md    # 核心机制文档
├── usage.md         # 使用文档
├── specs/           # 迭代规格 (Spec)
├── skills/          # 开发能力 (Skill)
└── execution/       # 执行状态文件
```

## Skill 清单

| Skill | 版本 | 类型 | 说明 |
|-------|------|------|------|
| mgg-dev-skill | 1.0.0 | 功能 Skill | mgg 自身开发：CLI 功能、决策通道、测试 |

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2026-07-16 | 初始版本，基于 ADE V2.0 规范建立 |
| 1.1.0 | 2026-07-16 | 迭代4: 模块化拆分(mgg.py→8模块包)、并行调度(ThreadPoolExecutor)、测试补齐(112测试/91%覆盖) |
| 1.2.0 | 2026-07-16 | 迭代5: 预分析决策(Preflight)，执行前分析决策点→批量确认→注入执行 |
