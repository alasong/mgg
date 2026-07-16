# mgg 核心机制文档

## 1. 任务生命周期

```
mgg run "prompt"
  │
  ├── [Plan] 参数解析
  │   ├── prompt + skill 推理
  │   ├── --dep 依赖检查
  │   └── --inject 决策注入
  │
  ├── [Execute] Claude 子进程
  │   ├── batch: claude -p "prompt" --no-session-persistence
  │   └── interactive: claude -p "prompt" --session <id>
  │
  ├── [Parse] 输出解析
  │   ├── NDJSON line 解析 → text + cost + session_id
  │   └── 非 JSON 行作为文本累加
  │
  ├── [Decide] 决策处理
  │   ├── batch: 事后提取 → 用户选择 → 保存 decision.json
  │   ├── interactive: 每轮循环 → 用户选择 → 继续会话 → 合并
  │   └── --inject: 读取前序 decision.json → 注入 prompt
  │
  └── [Persist] 状态持久化
      ├── state.json: 任务元信息
      ├── result.md: 执行结果
      └── decision.json: 决策记录（可选）
```

## 2. 决策通道

### 2.1 事后决策模式（batch）

```
Claude 输出 → NDJSON 解析
  → _extract_decision_from_output(text)
    → JSON 代码块匹配: ```json {...options...} ```
    → Markdown 表格匹配: | 方案 | 优点 | 缺点 |
  → 校验: ≥2 个选项, 有 id 和 label
  → _prompt_human_for_decision() → input()
  → _save_decision() → decision.json
```

### 2.2 实时交互模式（interactive）

```
_run_interactive_loop(prompt, skill)
  │
  ├── Round 1: _run_claude_with_session(prompt, skill, session_id=None)
  │   ├── 生成新 session, 获取 session_id
  │   └── 解析输出, 提取 latest_text
  │
  └── Round 2-N (最多 MAX_INTERACTIVE_ROUNDS=5 轮):
      ├── _extract_decision_from_output(latest_text)  ← 只检查最新一轮
      ├── 有决策 → _prompt_human_for_decision() → 用户选择
      │       → _run_claude_with_session(follow_prompt, skill=None, session_id)
      │       → 合并 text + 累加 cost
      └── 无决策 → 结束循环
```

**关键设计：** 每次只检查最新一轮的文本（`latest_text`），避免积压文本中的历史决策被重复提取。

### 2.3 决策注入（--inject）

```
pre-task → decision.json
  → --inject pre_task_id
    → _load_decision(task_dir) → {"decision": ..., "choice": "A"}
      → _inject_decision_into_prompt(prompt, data)
        → "当前prompt\n\n[决策注入] 问题 → 选择: label"
```

## 3. Skill 路由

```
_infer_skill(prompt):
  prompt_lower = prompt.lower()
  
  if "审查"|"review"|"audit" in prompt_lower → "paa"
  if "并行"|"parallel"|"多个" in prompt_lower  → "pdu"
  if "tdd"|"测试驱动" in prompt_lower          → "ulw"
  if "流程"|"多步"|"pipeline" in prompt_lower  → "pfs"
  if "分析"|"research"|"调研" in prompt_lower  → "pff"
  
  default → "pdu"
```

按关键词顺序匹配，命中即返。因此关键词在 prompt 中的顺序重要——"分析并审查代码"会走 `paa`（审查先匹配）。

## 4. Claude 子进程管理

### 批处理模式
```python
args = ["claude", "-p", f"/{skill} {prompt}",
        "--output-format", "json",
        "--permission-mode", "auto",
        "--no-session-persistence"]
result = subprocess.run(args, capture_output=True, text=True)
```

### 会话模式
```python
args = ["claude", "-p", prompt,
        "--output-format", "json",
        "--permission-mode", "auto",
        "--session", session_id]
# 注意: 省略 --no-session-persistence, session 在 ~/.claude/sessions/ 持久化
```

## 5. NDJSON 输出解析

Claude Code 的 `--output-format json` 输出是每行一个 JSON 对象的 NDJSON 流：

```jsonl
{"type":"progress","pct":50}
{"type":"result","result":"task output text","session_id":"sess_xxx","total_cost_usd":0.05}
```

`_parse_claude_output` 处理逻辑：
- **JSON 行 + type=result** → 提取 `result`(文本)、`session_id`、`total_cost_usd`、`errors`
- **JSON 行 + 其他 type** → 作为协议事件，不进入文本
- **非 JSON 行** → 累加到文本
- **多个 result 行** → 文本拼接，cost 取最后一行

## 6. 持久化机制

```
.mgg/tasks/<task_id>/
├── state.json       # 任务状态（JSON）
│   ├── id           # 12 位 hex
│   ├── prompt       # 原始 prompt
│   ├── skill        # 路由到的 skill
│   ├── status       # running / done / failed
│   ├── cost_usd     # Claude API 成本
│   ├── session_id   # 会话 ID
│   ├── exit_code    # 子进程退出码
│   ├── error        # 错误信息
│   ├── dependencies # 依赖任务 ID 列表
│   └── inject       # 注入的决策任务 ID
├── result.md        # 执行结果（文本）
└── decision.json    # 决策记录（可选）
    ├── decision     # 原始决策结构体
    ├── choice       # 用户选择的选项 ID
    ├── choice_label # 选项标签
    └── decided_at   # 决策时间
```
