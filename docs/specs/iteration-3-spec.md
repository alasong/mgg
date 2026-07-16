# 迭代3 Spec — CLI 集成测试覆盖

## 元信息
- **Spec名称**: 迭代3 Spec
- **类型**: 迭代
- **版本**: 1.0.0
- **前置条件**: 迭代2 完成（决策通道实时交互）
- **输出产物**: CLI 命令层集成测试 + 覆盖率 ≥ 70%
- **执行状态文件**: `docs/execution/iteration-3-status.md`

## 依赖Skill
- mgg 开发 Skill (`docs/skills/mgg-dev-skill.md`)

## PDCA执行步骤

### Plan (规划)
- **目标**: 补全 CLI 命令层测试，覆盖 cmd_run、cmd_status、cmd_ls、cmd_resume、cmd_decide 的 mock 集成测试
- **范围**:

| 命令 | 测试场景 | 当前覆盖 |
|------|---------|---------|
| cmd_run | 正常完成 / 失败 / --dep / --inject / --interactive | 无 |
| cmd_status | 有任务 / 无任务 / 指定任务ID | 部分 |
| cmd_ls | 有 skill / 无 skill | 部分 |
| cmd_resume | 重跑失败任务 | 无 |
| cmd_decide | 为任务记录决策 | 无 |
| main() | argparse 解析 | 无 |

### Do (执行)
- **活动**:
  1. `test_cmd_run.py` — mock subprocess.run，覆盖正常/失败/dep/inject/interactive
  2. `test_cmd_status.py` — 用临时目录创建 task state.json 测试列表/详情
  3. `test_cmd_ls.py` — 已有，补充边界
  4. `test_cmd_resume.py` — 重跑失败任务，验证 state 被重置
  5. `test_cmd_decide.py` — 为已有任务记录决策
  6. 全程 TDD: Red → Green → Refactor
- **输出**: 5-8 个新测试文件 / 15-25 个新测试用例

### Check (验证)
- **活动**:
  1. `python3 -m pytest tests/ -n auto -q` 全部通过
  2. 覆盖率 ≥ 70%
  3. 核心模块覆盖率 ≥ 85%
- **输出**: 测试报告 + 覆盖率报告

### Act (改进)
- **活动**: 补充边界测试、更新 AGENT.MD 和 Skill 清单
- **输出**: 最终版测试套件
