"""Tests for _prompt_human_for_decision (stdin interaction, uncovered 17%)."""

from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.decision import _prompt_human_for_decision


def test_prompt_returns_choice():
    """Valid option input returns the choice."""
    decision = {
        "question": "pick one",
        "options": [
            {"id": "A", "label": "Option A", "pros": "fast", "cons": "costly"},
            {"id": "B", "label": "Option B", "pros": "simple", "cons": "limited"},
        ]
    }
    with patch("builtins.input", return_value="A"):
        result = _prompt_human_for_decision("task_1", decision)
        assert result == "A"


def test_prompt_skip_returns_none():
    """Empty input skips the decision."""
    decision = {
        "question": "pick one",
        "options": [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}],
    }
    with patch("builtins.input", return_value=""):
        result = _prompt_human_for_decision("task_1", decision)
        assert result is None


def test_prompt_eof_error_returns_none():
    """EOFError returns None without crashing."""
    decision = {
        "question": "pick",
        "options": [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}],
    }
    with patch("builtins.input", side_effect=EOFError()):
        result = _prompt_human_for_decision("task_1", decision)
        assert result is None


def test_prompt_keyboard_interrupt_returns_none():
    """KeyboardInterrupt returns None without crashing."""
    decision = {
        "question": "pick",
        "options": [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}],
    }
    with patch("builtins.input", side_effect=KeyboardInterrupt()):
        result = _prompt_human_for_decision("task_1", decision)
        assert result is None


def test_prompt_displays_question_and_options(capsys):
    """Prompt output contains question and option details."""
    decision = {
        "question": "What to do?",
        "options": [
            {"id": "X", "label": "Plan X", "pros": "cheap", "cons": "slow"},
        ]
    }
    with patch("builtins.input", return_value="X"):
        _prompt_human_for_decision("t1", decision)
    captured = capsys.readouterr()
    assert "What to do?" in captured.out
    assert "Plan X" in captured.out
    assert "cheap" in captured.out
    assert "slow" in captured.out
