"""Tests for decision channel prototype (decision extraction, persistence, injection)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg import (
    _extract_decision_from_output,
    _save_decision,
    _load_decision,
    _inject_decision_into_prompt,
)


# ── _extract_decision_from_output ──────────────────────────────────────


def test_extract_json_decision_block():
    """Extract explicit JSON decision block with options/choices."""
    text = """分析完成，以下是选项：

```json
{
  "question": "选哪个缓存方案？",
  "options": [
    {"id": "A", "label": "Redis", "pros": "快", "cons": "吃内存"},
    {"id": "B", "label": "Memcached", "pros": "简单", "cons": "功能少"}
  ]
}
```

请选择。
"""
    result = _extract_decision_from_output(text)
    assert result is not None, "should extract decision block"
    assert result["question"] == "选哪个缓存方案？"
    assert len(result["options"]) == 2
    assert result["options"][0]["id"] == "A"


def test_extract_markdown_decision():
    """Extract decision from structured markdown section."""
    text = """
## 决策点

问题：使用什么数据库？

| 方案 | 优点 | 缺点 |
|------|------|------|
| A: Postgres | 成熟稳定 | 扩展复杂 |
| B: SQLite | 零配置 | 并发差 |

请选择 A 或 B。
"""
    result = _extract_decision_from_output(text)
    assert result is not None
    assert "数据库" in result["question"]
    assert len(result["options"]) >= 2


def test_extract_no_decision():
    """Return None when no decision point is detected."""
    text = """这是一个普通分析结果。没有需要决策的内容。"""
    result = _extract_decision_from_output(text)
    assert result is None


def test_extract_partial_decision():
    """Handle malformed or partial decision data gracefully."""
    text = '{"question": "测试", "options": null}'
    result = _extract_decision_from_output(text)
    assert result is None, "should reject invalid decision structure"


def test_extract_no_code_fence_json():
    """Handle bare ``` fences without 'json' tag."""
    text = '```\n{"question": "选?", "options": [{"id": "A", "label": "方案A"}, {"id": "B", "label": "方案B"}]}\n```'
    result = _extract_decision_from_output(text)
    assert result is not None


def test_extract_string_options():
    """Handle options as list of strings (not dicts)."""
    text = '```json\n{"question": "pick", "options": ["A", "B", "C"]}\n```'
    result = _extract_decision_from_output(text)
    assert result is not None
    assert len(result["options"]) == 3
    assert result["options"][0]["id"] == "A"


def test_extract_table_with_simple_header():
    """Extract from markdown table with '方案' header."""
    text = """## 缓存方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| A: Redis | 快 | 内存大 |
| B: Local | 简单 | 慢 |

请选择。
"""
    result = _extract_decision_from_output(text)
    assert result is not None
    assert len(result["options"]) == 2


def test_extract_table_section_header_as_question():
    """Use section header as question when no explicit question line."""
    text = """## Pick one

| option | description |
|--------|-------------|
| X: Foo | does this |
| Y: Bar | does that |
"""
    result = _extract_decision_from_output(text)
    assert result is not None
    assert "Pick one" in result["question"]


# ── _save_decision / _load_decision ────────────────────────────────────


def test_save_and_load_decision():
    """Save then load returns identical data."""
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp) / "tasks" / "abc123"
        task_dir.mkdir(parents=True)

        decision = {"question": "测试?", "options": [{"id": "A", "label": "方案A"}]}
        choice = "A"

        _save_decision(task_dir, decision, choice)
        loaded = _load_decision(task_dir)

        assert loaded is not None
        assert loaded["decision"]["question"] == "测试?"
        assert loaded["choice"] == "A"


def test_load_nonexistent_decision():
    """Loading decision from task with no decision returns None."""
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp) / "tasks" / "nonexistent"
        result = _load_decision(task_dir)
        assert result is None


def test_load_corrupted_decision():
    """Loading corrupted decision file returns None without crashing."""
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp) / "tasks" / "corrupted"
        task_dir.mkdir(parents=True)
        (task_dir / "decision.json").write_text("{bad json")
        result = _load_decision(task_dir)
        assert result is None


# ── _inject_decision_into_prompt ───────────────────────────────────────


def test_inject_decision():
    """Inject decision into prompt string."""
    decision_data = {
        "decision": {"question": "选哪个?", "options": [{"id": "A", "label": "Redis"}]},
        "choice": "A",
        "choice_label": "Redis",
    }
    prompt = "实现方案"
    result = _inject_decision_into_prompt(prompt, decision_data)
    assert "选哪个?" in result
    assert "Redis" in result
    assert prompt in result


def test_inject_no_decision():
    """Inject with None data returns original prompt unchanged."""
    prompt = "实现方案"
    result = _inject_decision_into_prompt(prompt, None)
    assert result == prompt
