"""Tests for task state management (_save_task, _load_task, die, _find_choice_label)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.persistence import _save_task, _load_task, _find_choice_label
from mgg.utils import die, _print_status_line


def test_save_and_load_task():
    """Save task state then load it back."""
    task = {"id": "test123", "prompt": "do something", "status": "running", "skill": "pdu"}
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.persistence.TASKS_DIR", Path(tmp) / "tasks"):
            _save_task(task)
            loaded = _load_task("test123")
            assert loaded["id"] == "test123"
            assert loaded["prompt"] == "do something"
            assert loaded["status"] == "running"


def test_load_nonexistent():
    """Load non-existent task raises SystemExit."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.persistence.TASKS_DIR", Path(tmp) / "tasks"):
            try:
                _load_task("no_such_task")
                assert False, "should have raised SystemExit"
            except SystemExit:
                pass


def test_save_updates_existing():
    """Save with existing task ID overwrites previous state."""
    task = {"id": "test456", "status": "running"}
    updated = {"id": "test456", "status": "done", "result": "ok"}
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.persistence.TASKS_DIR", Path(tmp) / "tasks"):
            _save_task(task)
            _save_task(updated)
            loaded = _load_task("test456")
            assert loaded["status"] == "done"
            assert loaded["result"] == "ok"


def test_die_exits_with_message():
    """die() prints to stderr and exits with code 1."""
    with patch("sys.stderr") as mock_stderr:
        try:
            die("error msg")
            assert False, "should have exited"
        except SystemExit as e:
            assert e.code == 1


def test_find_choice_label_by_id():
    """Find label for existing option id."""
    decision = {
        "question": "test",
        "options": [
            {"id": "A", "label": "Option A"},
            {"id": "B", "label": "Option B"},
        ]
    }
    assert _find_choice_label(decision, "A") == "Option A"
    assert _find_choice_label(decision, "B") == "Option B"


def test_find_choice_label_missing():
    """Return the id itself when option not found."""
    decision = {
        "question": "test",
        "options": [{"id": "A", "label": "Option A"}]
    }
    assert _find_choice_label(decision, "X") == "X"
    assert _find_choice_label(decision, "") == ""


def test_find_choice_label_no_options():
    """Return the choice id when options list is empty."""
    decision = {"question": "test", "options": []}
    assert _find_choice_label(decision, "A") == "A"


# ── _print_status_line ──────────────────────────────────────────────────


def test_status_line_done(capsys):
    """Done status prints checkmark."""
    state = {"id": "abc", "status": "done", "cost_usd": None, "error": None}
    _print_status_line(state)
    captured = capsys.readouterr()
    assert "✓" in captured.out
    assert "abc" in captured.out


def test_status_line_failed(capsys):
    """Failed status prints X mark and error."""
    state = {"id": "abc", "status": "failed", "cost_usd": None, "error": "timeout"}
    _print_status_line(state)
    captured = capsys.readouterr()
    assert "✗" in captured.out
    assert "timeout" in captured.out


def test_status_line_with_cost(capsys):
    """Status line includes cost when available."""
    state = {"id": "x1", "status": "done", "cost_usd": 0.05, "error": None}
    _print_status_line(state)
    captured = capsys.readouterr()
    assert "$0.050" in captured.out
