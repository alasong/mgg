# mgg 开发 Skill

> mgg 项目自身开发的标准化流程。用于实现 mgg CLI 新功能、修改现有逻辑、添加测试。

## 元信息
- **Skill名称**: mgg-dev-skill
- **类型**: 功能 Skill
- **版本**: 1.0.0
- **适用场景**: 开发 mgg 项目自身

## Skill 依赖
- 测试框架: pytest + pytest-xdist

## PDCA 执行步骤

### Plan (规划)
- **输入**: 要开发的功能描述 / Spec 引用
- **活动**:
  1. 理解 AGENT.MD 中的架构规范和编码规范
  2. 确定要修改或新增的函数/模块
  3. 编写测试用例清单（正常路径 + 边界 + 异常）
- **输出**: 测试用例清单

### Do (执行)
- **活动**: 按 TDD 流程执行
  1. 每个独立功能走 Red → Green → Refactor
  2. 先写测试（assert 预期行为）
  3. 再实现最少代码让测试通过
  4. 最后重构（清理、提取、优化）
- **输出**: 功能实现 + 测试代码

**TDD 要求：**
```
1. Red: 写一个会失败的测试 → 运行确认失败
2. Green: 写最少代码让测试通过 → 运行确认通过
3. Refactor: 重构代码 → 运行确认测试仍通过
```

**测试约定：**
- 测试文件放在 `tests/` 目录，命名为 `test_*.py`
- 核心模块测试优先：
  - 决策通道：`test_decision_channel.py`
  - 输出解析：`test_output_parser.py`
  - Skill 路由：`test_skill_router.py`
  - 状态管理：`test_task_state.py`
- 使用 `pytest` + `-n auto` 并行执行

### Check (验证)
- **输入**: 实现代码 + 测试代码
- **活动**:
  1. 运行 `python3 -m pytest tests/ -n auto -q`
  2. 检查覆盖率: `python3 -m pytest tests/ --cov=mgg.py`
  3. 验证核心模块覆盖率 ≥ 80%
- **输出**: 测试报告 + 覆盖率报告

### Act (改进)
- **活动**:
  1. 分析测试失败原因，修复
  2. 检查是否有未覆盖的边界场景
  3. 记录 TDD 日志到 `docs/execution/tdd-logs/`
- **输出**: 最终代码 + TDD 日志

## 变更记录
| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2026-07-16 | 初始版本 |
