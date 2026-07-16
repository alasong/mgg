"""Tests for _batch_prompt_human (stdin mock)."""

from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.analyzer import _batch_prompt_human


def test_batch_select_all():
    """User selects choices for all decisions."""
    decisions = [
        {"question": "选数据库?", "options": [
            {"id": "A", "label": "Postgres"},
            {"id": "B", "label": "SQLite"},
        ]},
        {"question": "选认证?", "options": [
            {"id": "A", "label": "JWT"},
            {"id": "B", "label": "Session"},
        ]},
    ]
    with patch("builtins.input", side_effect=["A", "A"]):
        result = _batch_prompt_human(decisions)
        assert result == {"选数据库?": "A", "选认证?": "A"}


def test_batch_skip_all():
    """User skips all decisions (empty input for each)."""
    decisions = [
        {"question": "选数据库?", "options": [
            {"id": "A", "label": "Postgres"},
            {"id": "B", "label": "SQLite"},
        ]},
    ]
    with patch("builtins.input", return_value=""):
        result = _batch_prompt_human(decisions)
        assert result == {}


def test_batch_no_decisions():
    """Empty decisions list returns empty dict."""
    result = _batch_prompt_human([])
    assert result == {}


def test_batch_displays_question(capsys):
    """Output contains question text and options."""
    decisions = [
        {"question": "选哪个?", "options": [
            {"id": "A", "label": "方案A"},
            {"id": "B", "label": "方案B"},
        ]},
    ]
    with patch("builtins.input", return_value="A"):
        _batch_prompt_human(decisions)
    captured = capsys.readouterr()
    assert "选哪个?" in captured.out
    assert "方案A" in captured.out
    assert "方案B" in captured.out
    assert "预分析" in captured.out
