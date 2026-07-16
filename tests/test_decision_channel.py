"""Tests for decision channel prototype (decision extraction, persistence, injection)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.decision import _extract_decision_from_output, _validate_decision_json, \
    _extract_markdown_decision_table, _inject_decision_into_prompt
from mgg.persistence import _save_decision, _load_decision


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


# ── _validate_decision_json edge cases ──────────────────────────────


def test_validate_non_dict_returns_none():
    """Non-dict input returns None."""
    assert _validate_decision_json("string") is None
    assert _validate_decision_json([]) is None


def test_validate_choices_key():
    """'choices' key is accepted like 'options'."""
    data = {"question": "pick", "choices": [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}]}
    result = _validate_decision_json(data)
    assert result is not None
    assert len(result["options"]) == 2


def test_validate_alternatives_key():
    """'alternatives' key is accepted."""
    data = {"question": "pick", "alternatives": [{"id": "X", "label": "X"}, {"id": "Y", "label": "Y"}]}
    result = _validate_decision_json(data)
    assert result is not None
    assert len(result["options"]) == 2


def test_validate_insufficient_options():
    """Fewer than 2 options returns None."""
    data = {"question": "pick", "options": [{"id": "A", "label": "Only"}]}
    result = _validate_decision_json(data)
    assert result is None


def test_validate_empty_options():
    """Empty options list returns None."""
    data = {"question": "pick", "options": []}
    result = _validate_decision_json(data)
    assert result is None


def test_validate_dict_options_name_description():
    """Dict options can use name/description keys."""
    data = {
        "prompt": "pick",
        "options": [
            {"name": "opt1", "description": "Option 1", "pro": "fast", "con": "costly"},
            {"name": "opt2", "description": "Option 2", "pro": "simple", "con": "limited"},
        ]
    }
    result = _validate_decision_json(data)
    assert result is not None
    assert result["question"] == "pick"
    assert result["options"][0]["id"] == "opt1"
    assert result["options"][0]["pros"] == "fast"
    assert result["options"][0]["cons"] == "costly"


def test_validate_title_as_question():
    """Uses title key when question/prompt not present."""
    data = {"title": "pick one", "options": ["A", "B"]}
    result = _validate_decision_json(data)
    assert result is not None
    assert result["question"] == "pick one"


def test_validate_non_list_options():
    """Options that is not a list returns None."""
    data = {"question": "pick", "options": "string"}
    result = _validate_decision_json(data)
    assert result is None


# ── _extract_markdown_decision_table edge cases ─────────────────────


def test_markdown_table_with_choice_header():
    """Markdown table with 'Choice' header is accepted."""
    text = """## 决策

| Choice | 说明 |
|--------|------|
| A: Plan A | does X |
| B: Plan B | does Y |
"""
    result = _extract_markdown_decision_table(text)
    assert result is not None
    assert len(result["options"]) == 2


def test_markdown_table_no_section():
    """No markdown section with table returns None."""
    text = "Plain text without any table or section."
    result = _extract_markdown_decision_table(text)
    assert result is None


def test_markdown_table_fewer_than_two_rows():
    """Fewer than 2 option rows returns None."""
    text = """## 决策

| 方案 | 说明 |
|------|------|
| A: Single | only one |
"""
    result = _extract_markdown_decision_table(text)
    assert result is None


# ── JSON code fence edge cases ─────────────────────────────────────


def test_json_code_fence_invalid_json():
    """Invalid JSON in code fence doesn't crash, returns None."""
    text = "分析：\n```json\n{invalid json here}\n```\n"
    result = _extract_decision_from_output(text)
    assert result is None


def test_json_code_fence_no_code_fence():
    """Bare JSON without code fence is not extracted."""
    text = '{"question": "pick", "options": [{"id":"A","label":"A"},{"id":"B","label":"B"}]}'
    result = _extract_decision_from_output(text)
    assert result is None
