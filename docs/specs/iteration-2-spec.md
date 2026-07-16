# 迭代2 Spec — 决策通道实时交互

## 元信息
- **Spec名称**: 迭代2 Spec
- **类型**: 迭代
- **版本**: 1.0.0
- **前置条件**: 迭代1 完成（ADE 基础设施 + 测试套件）
- **输出产物**: `mgg run --interactive` 实时决策交互功能 + 测试
- **质量标准**: 新增测试 ≥ 8 个，全部通过，核心功能覆盖
- **执行状态文件**: `docs/execution/iteration-2-status.md`

## 依赖Skill
- mgg 开发 Skill (`docs/skills/mgg-dev-skill.md`)

## PDCA执行步骤

### Plan (规划)
- **目标**: 实现决策通道实时交互，让 Claude 子进程遇到决策点时暂停等待人工输入
- **架构设计**:

### 架构

```
mgg run --interactive "prompt"
  │
  ├── 1. claude -p "prompt" --session <id>     (会话持久)
  │       └── 输出带决策块
  │
  ├── 2. 检测到决策块?
  │       ├── 是 → 展示选项给用户 → 获取选择
  │       │       └── claude -p "choice" --session <id>  (继续会话)
  │       │           └── 回到 2 (循环)
  │       └── 否 → 完成
  │
  └── 3. 合并所有轮次输出 → 保存结果
```

### Do (执行)

**活动**:
1. **`--interactive` 标志**
   - 给 `mgg run` 添加 `-i` / `--interactive` 参数
   - 开启后：省略 `--no-session-persistence`，保存 session_id
   - 保持现有行为不变

2. **决策循环引擎**
   - 新函数 `_run_interactive_loop(prompt, skill)`：
     - 第1轮：执行 claude 子进程（带 session）
     - 提取决策块
     - 如有决策 → 展示给用户 → 执行下一轮（`-p choice --session <id>`）
     - 重复直到无更多决策
   - 合并各轮 result_text

3. **交互提示格式化**
   - 美观的决策展示（编号 + 优缺点 + 输入选择）
   - 支持多轮决策（每轮独立上下文）

4. **结果合并**
   - 多轮输出拼接为完整 result.md
   - 保留最终 session_id、累加 cost

**TDD 顺序**:
```
1. 构建 interactive 参数测试
2. 决策循环引擎（单轮、多轮）
3. 结果合并
4. 集成测试（mock subprocess）
```

- **输出**: interactive 模式完整实现 + 测试

### Check (验证)
- **输入**: mgg.py 源码 + 新增测试
- **活动**:
  1. `python3 -m pytest tests/ -n auto -q` 全部通过
  2. 交互模式核心逻辑覆盖
  3. 非交互模式行为不变
- **输出**: 测试通过 + 行为验证

### Act (改进)
- **活动**:
  1. 补充缺失的边界测试
  2. 优化交互格式
  3. 更新 AGENT.MD Skill 清单
- **输出**: 最终版决策通道

## 变更记录
| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0.0 | 2026-07-16 | 初始版本 | ADE |
