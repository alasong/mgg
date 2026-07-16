"""Integration tests for full preflight pipeline: analyze → confirm → inject → execute."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from argparse import Namespace
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.analyzer import _build_injection_text, _preflight_analyze


def _fake_result(returncode=0, stdout=""):
    """Simple result object, no MagicMock."""
    class _R:
        pass
    r = _R()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = ""
    return r


def test_build_injection_text():
    """Build injection text from decisions dict."""
    choices = {"选数据库?": "A"}
    decisions = [
        {"question": "选数据库?", "options": [
            {"id": "A", "label": "Postgres"},
            {"id": "B", "label": "SQLite"},
        ]},
    ]
    text = _build_injection_text(decisions, choices)
    assert "选数据库?" in text
    assert "Postgres" in text
    assert "A" in text


def test_build_injection_text_no_choices():
    """Empty choices returns just the marker."""
    text = _build_injection_text([], {})
    assert "已确认决策" in text


def test_preflight_skip_flag():
    """--no-preflight flag skips preflight analysis in cmd_run."""
    from mgg.cli import cmd_run

    args = Namespace(prompt=["测试任务"], skill=None, no_skill=False,
                     dep=[], inject=None, interactive=False,
                     parallel=False, max_workers=3,
                     no_preflight=True)

    mock_state = {
        "id": "fake", "prompt": "测试任务", "skill": "pdu",
        "status": "done", "exit_code": 0, "cost_usd": 0.05,
        "session_id": "s1", "error": None,
        "finished_at": "now", "created_at": "now",
        "dependencies": [], "inject": None,
    }
    mock_parsed = {"text": "ok", "cost_usd": 0.05, "session_id": "s1", "errors": []}

    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.cli.TASKS_DIR", Path(tmp) / "tasks"), \
             patch("mgg.persistence.TASKS_DIR", Path(tmp) / "tasks"), \
             patch("mgg.executor.TASKS_DIR", Path(tmp) / "tasks"), \
             patch("mgg.analyzer.TASKS_DIR", Path(tmp) / "tasks"), \
             patch("mgg.cli._run_single_task",
                   return_value=(mock_state, mock_parsed)), \
             patch("mgg.analyzer.subprocess.run") as mock_pre:
            result = cmd_run(args)
            mock_pre.assert_not_called()
            assert result is not None
            assert result["status"] == "done"
