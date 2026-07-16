"""Tests for _wait_dependencies (time-based polling, uncovered 17%)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.utils import _wait_dependencies


def _make_task(tasks_dir: Path, task_id: str, status: str):
    """Create a task state file in the tasks dir."""
    td = tasks_dir / task_id
    td.mkdir(parents=True, exist_ok=True)
    state = {"id": task_id, "status": status, "prompt": "test"}
    (td / "state.json").write_text(json.dumps(state))


def test_no_dependencies():
    """Empty dependency list returns immediately."""
    _wait_dependencies([])


def test_dependencies_already_done():
    """All dependencies already done returns immediately."""
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp) / "tasks"
        with patch("mgg.persistence.TASKS_DIR", tasks_dir):
            _make_task(tasks_dir, "a", "done")
            _make_task(tasks_dir, "b", "done")
            _wait_dependencies(["a", "b"])


def test_dependency_becomes_done():
    """Pending dependency is waited on then returns when done."""
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp) / "tasks"
        with patch("mgg.persistence.TASKS_DIR", tasks_dir):
            _make_task(tasks_dir, "a", "running")

            call_count = [0]

            def _mock_sleep(secs):
                call_count[0] += 1
                if call_count[0] >= 1:
                    _make_task(tasks_dir, "a", "done")

            with patch("time.sleep", side_effect=_mock_sleep):
                _wait_dependencies(["a"])

            assert call_count[0] >= 1


def test_failed_dependency_is_done():
    """Failed dependencies are treated as resolved (don't block)."""
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp) / "tasks"
        with patch("mgg.persistence.TASKS_DIR", tasks_dir):
            _make_task(tasks_dir, "a", "failed")
            _wait_dependencies(["a"])
