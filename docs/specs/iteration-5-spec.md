# 迭代5 Spec — 预分析决策（Preflight Decision Mode）

## 元信息
- **Spec名称**: 迭代5 Spec
- **类型**: 迭代
- **版本**: 1.0.0
- **前置条件**: 迭代4 完成（模块化 mgg 包 + 并行调度 + 覆盖率 ≥ 90%）
- **输出产物**: 预分析决策模式（先分析 Prompt 所需的决策点 → 用户确认 → 带决策执行）
- **质量标准**: 全部测试通过，覆盖率 ≥ 90%，预分析 + 兜底追问双路径集成测试

## 依赖Skill
- mgg 开发 Skill (`docs/skills/mgg-dev-skill.md`)

## PDCA执行步骤

### Plan (规划)

**目标**: 在 `mgg run` 中新增预分析阶段 —— 执行主任务前，让 Claude 先对 prompt 做轻量分析，估算出需要用户确认的决策点，用户确认后再注入 prompt 执行。同时保留执行中意外决策的兜底追问。

#### 架构变更

**新增 `mgg/analyzer.py` 模块**：

```
mgg/analyzer.py
  ├── _preflight_analyze(prompt) → list[decision]   # 轻量 Claude 调用，分析决策点
  └── _batch_prompt_human(decisions) → dict[id->choice]  # 批量确认界面
```

**修改 `cli.py` `cmd_run`**：

```
cmd_run 的完整流程：

                      ┌─ 传统模式（--no-preflight 跳过）
                      │
用户输入 prompt ─→ 预分析阶段（默认开启）
                      │   Claude 轻量分析 → 提取预期决策点
                      │   → 批量展示给用户确认
                      │   → 用户选完 → 注入 prompt
                      │
                      ├─ 执行阶段（子进程）
                      │   若产出未预料的决策 → 兜底事后追问（已有逻辑）
                      │
                      └─ 完成
```

**关键约束**：
- 预分析是单独一次轻量 Claude 调用（`claude -p "分析以下任务需要哪些决策点..."`），不是完整子进程
- 预分析结果可绕过（`--no-preflight`）
- 预分析识别出的决策点用 JSON 结构体注入 prompt 头，Claude 能直接消费
- 兜底事后追问保持不动（已有 `_extract_decision_from_output` 逻辑）

### Do (执行)

**A 组：预分析模块（analyzer.py）**

| # | 任务 | 内容 |
|---|------|------|
| 1 | `_preflight_analyze(prompt)` | 拼装预分析 prompt → `subprocess.run(["claude", "-p", ...])` → 解析返回的 JSON 决策列表 |
| 2 | `_batch_prompt_human(decisions)` | 一次性展示多个决策点，每个让用户选。支持全部跳过、逐个选择 |
| 3 | 决策注入到主 prompt | 把预分析结果格式化为 `[已确认决策]\n1. ...\n2. ...\n` 注入到主 prompt 头部 |

**B 组：cli.py 集成**

| # | 任务 | 内容 |
|---|------|------|
| 1 | `cmd_run` 预分析分支 | 默认开启，`--no-preflight` 跳过；分析出的决策批量展示 |
| 2 | argparse 参数 | `--no-preflight` flag |
| 3 | 交互流程集成 | 预分析产出 0 个决策 → 直接执行；有决策 → 展示确认 → 注入执行 |
| 4 | 执行中兜底 | 跑完后仍走 `_extract_decision_from_output` 检查未预料的决策 |

**C 组：测试**

| # | 任务 | 类型 | 预期测试数 |
|---|------|------|-----------|
| 1 | `test_analyzer.py` | subprocess mock 覆盖 `_preflight_analyze` | 4 |
| 2 | `test_analyzer_prompt.py` | stdin mock 覆盖批量确认界面 | 3 |
| 3 | `test_preflight_integration.py` | 全链路：预分析 → 用户选 → 注入 → 执行 → 兜底 | 3 |

### Check (验证)

**活动**:
1. `python3 -m pytest tests/ -n auto -q` 全部通过（≥ 112 + 10 = ≥ 122 个）
2. 覆盖率 ≥ 90%（新增 analyzer.py ≥ 95%）
3. 集成测试：预分析产出的决策正确注入到主 prompt
4. 回退测试：`--no-preflight` 行为与迭代4 完全一致
5. 兜底事后追问不影响

### Act (改进)

**活动**:
1. 评估预分析准确率——是否漏判或多判决策点
2. 如果有明显漏判，优化 `_preflight_analyze` 的提示词模板
3. 更新 features.md 和 architecture.md
4. 更新 execution/iteration-5-status.md

## 变更记录
| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0.0 | 2026-07-16 | 初始版本 | ADE |
