# 迭代1 Spec — 建立 ADE 开发基础设施 + mgg 测试覆盖

## 元信息
- **Spec名称**: 迭代1 Spec
- **类型**: 迭代
- **版本**: 1.0.0
- **前置条件**: 无
- **输出产物**: AGENT.MD + docs/ 目录结构 + mgg-dev-skill + 执行状态文件 + mgg 单元测试
- **质量标准**: 测试覆盖率 ≥ 60%，测试全部通过
- **执行状态文件**: `docs/execution/iteration-1-status.md`

## 依赖Skill
- mgg 开发 Skill (`docs/skills/mgg-dev-skill.md`)

## PDCA执行步骤

### Plan (规划)
- **目标**: 初始化 ADE V2.0 项目基础设施，为 mgg 建立可复用的开发流程
- **输入**: ADE V2.0 发布包（`release/v2.0.0/`）
- **活动**:
  1. 创建 AGENT.MD，定义项目架构、技术栈、规范
  2. 创建 `docs/specs/`、`docs/skills/`、`docs/execution/` 目录
  3. 创建迭代1 Spec（本文档）
  4. 创建 mgg-dev-skill
  5. 创建迭代1 执行状态文件
- **输出**: 项目规范 + 文档目录 + Spec + Skill + 执行状态

### Do (执行)
- **输入**: mgg.py 源码 + pytest + pytest-xdist
- **活动**:
  1. 按 mgg-dev-skill 的 TDD 流程为 mgg.py 编写测试
  2. 核心模块测试覆盖：决策通道解析、输出解析、Skill 路由
  3. 边界场景测试：空输出、非法 JSON、依赖等待超时
  4. 验证 `python3 -m pytest tests/ -n auto -q` 全部通过
- **输出**: mgg 项目测试套件

### Check (验证)
- **输入**: 测试代码 + mgg.py
- **活动**:
  1. 运行全部测试，确认通过
  2. 检查测试覆盖率 ≥ 60%
  3. 验证核心模块（决策通道、输出解析）覆盖率 ≥ 80%
  4. 审查测试用例是否覆盖边界场景
- **输出**: 测试报告 + 覆盖率报告

### Act (改进)
- **输入**: 测试报告 + 覆盖率报告
- **活动**:
  1. 补充缺失的边界测试
  2. 优化 mgg-dev-skill 流程描述
  3. 更新 AGENT.MD 中的 Skill 清单
  4. 记录 TDD 日志
- **输出**: 最终版测试套件 + 技能优化 + TDD 日志

## 变更记录
| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0.0 | 2026-07-16 | 初始版本 | ADE |
