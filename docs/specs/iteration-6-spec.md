# 迭代 6 — 声明式技能配置（Routing + Config）

## 目标

将 mgg 中剩余的硬编码逻辑迁移到 SKILL.md 声明式元数据中，延续迭代 5 的 `decisions:` 模式。

## 变更范围

### 1. Routing Keywords（P0）
**问题**: `router.py:_infer_skill` 硬编码了 6 个技能的关键词 if/elif 链。新技能想被自动路由必须改 Python 代码。

**方案**: 每个 SKILL.md 声明 `routing.keywords`：
```yaml
routing:
  keywords: ["审查", "review", "audit"]
```

`_infer_skill` 改为遍历 `_discover_skills()`，检查每个技能的 `routing.keywords`，首匹配即返回。无匹配时回退 `"pdu"`（默认）。

- 消消硬编码映射代码 ~12 行
- 新技能只需加 SKILL.md 字段即注册路由
- 向后兼容：无 `routing` 字段的技能被跳过

### 2. max_workers（P1）
**问题**: 并行任务默认 `max_workers=3` 硬编码，每个并行技能需手动 `--max-workers`。

**方案**: SKILL.md 声明 `max_workers: 5`，`cmd_run` 在未显式传 `--max-workers` 时读取技能配置覆盖。

### 3. max_interactive_rounds（P2）
**问题**: `MAX_INTERACTIVE_ROUNDS = 5` 硬编码，所有技能共享同一上限。

**方案**: SKILL.md 声明 `max_interactive_rounds: 10`，`_run_interactive_loop` 读取技能配置覆盖。

## 受影响文件

| 文件 | 变更 |
|------|------|
| `mgg/router.py` | `_parse_skill_meta` 新增字段 whitelist；`_infer_skill` 重写为动态路由 |
| `mgg/executor.py` | `_run_interactive_loop` 读取 `max_interactive_rounds` |
| `mgg/cli.py` | `cmd_run` 并行模式读取 `max_workers` |
| `~/.claude/skills/paa/SKILL.md` | 新增 `routing` + `max_interactive_rounds` |
| `~/.claude/skills/pdu/SKILL.md` | 新增 `routing` + `max_workers` |
| `~/.claude/skills/pfs/SKILL.md` | 新增 `routing` |
| `~/.claude/skills/pff/SKILL.md` | 新增 `routing` + `max_interactive_rounds` |
| `~/.claude/skills/ulw/SKILL.md` | 新增 `routing` + `max_workers` + `max_interactive_rounds` |

## 不做

- `preflight_timeout` → 价值低，无实际需求
- `post_execution_decisions` → 价值低

## 测试计划

- 现有 127 测试应全部通过（行为不变）
- 新增测试：`test_parse_skill_meta` 验证 routing/config 字段
- 新增测试：`_infer_skill` 在 temp SKILLS_DIR 下验证动态路由
