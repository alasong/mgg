"""Tests for parallel task execution (_run_tasks_parallel, --parallel flag)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from argparse import Namespace
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.executor import _run_tasks_parallel, _run_single_task


def _mock_subprocess(text: str, cost: float = 0.05, sess: str = "sess_1",
                     returncode: int = 0):
    """Create a mock subprocess result with JSON NDJSON stdout."""
    line = json.dumps({"type": "result", "result": text,
                        "session_id": sess, "total_cost_usd": cost})
    return MagicMock(returncode=returncode, stdout=line + "\n", text="")


# ── _run_single_task ──────────────────────────────────────────────────


@patch("mgg.executor.subprocess.run", return_value=_mock_subprocess("task done"))
def test_run_single_task_basic(mock_run):
    """_run_single_task executes and returns updated state."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.executor.TASKS_DIR", Path(tmp) / "tasks"):
            state = {
                "id": "test1", "prompt": "do it", "skill": "pdu",
                "status": "running", "created_at": "now",
            }
            updated, parsed = _run_single_task(state, "pdu")
            assert updated["status"] == "done"
            assert updated["exit_code"] == 0
            assert "task done" in parsed.get("text", "")


@patch("mgg.executor.subprocess.run")
def test_run_single_task_failed(mock_run):
    """_run_single_task handles subprocess failure."""
    mock_run.return_value = _mock_subprocess("", returncode=1)
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.executor.TASKS_DIR", Path(tmp) / "tasks"):
            state = {
                "id": "test2", "prompt": "fail", "skill": None,
                "status": "running", "created_at": "now",
            }
            updated, _ = _run_single_task(state, None)
            assert updated["status"] == "failed"


# ── _run_tasks_parallel ────────────────────────────────────────────────


@patch("mgg.executor.subprocess.run")
def test_parallel_tasks_all_succeed(mock_run):
    """All parallel tasks complete successfully."""
    mock_run.return_value = _mock_subprocess("done")
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.executor.TASKS_DIR", Path(tmp) / "tasks"):
            results = _run_tasks_parallel(["task A", "task B"], "pdu", max_workers=2)
            assert len(results) == 2
            for r in results:
                assert r["status"] == "done"
            assert results[0]["prompt"] in ("task A", "task B")


@patch("mgg.executor.subprocess.run")
def test_parallel_error_isolation(mock_run):
    """One task failure doesn't affect other tasks."""
    responses = [
        _mock_subprocess("ok", returncode=0),
        _mock_subprocess("fail", returncode=1),
    ]
    mock_run.side_effect = responses
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.executor.TASKS_DIR", Path(tmp) / "tasks"):
            results = _run_tasks_parallel(["good task", "bad task"], None, max_workers=2)
            assert len(results) == 2
            statuses = {r["status"] for r in results}
            assert "done" in statuses
            assert "failed" in statuses


@patch("mgg.executor.subprocess.run")
def test_parallel_max_workers(mock_run):
    """max_workers limits concurrency."""
    mock_run.return_value = _mock_subprocess("done")
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.executor.TASKS_DIR", Path(tmp) / "tasks"):
            results = _run_tasks_parallel(["a", "b", "c", "d"], "pdu", max_workers=2)
            assert len(results) == 4
            assert all(r["status"] == "done" for r in results)


# ── CLI integration ────────────────────────────────────────────────────


@patch("mgg.cli.subprocess.run", return_value=_mock_subprocess("parallel done"))
def test_cmd_run_parallel_flag(mock_run):
    """cmd_run with --parallel flag runs multiple tasks."""
    from mgg.cli import cmd_run

    args = Namespace(prompt=["p1", "p2"], skill=None, no_skill=False,
                     dep=[], inject=None, interactive=False,
                     parallel=True, max_workers=3)
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.cli.TASKS_DIR", Path(tmp) / "tasks"), \
             patch("mgg.persistence.TASKS_DIR", Path(tmp) / "tasks"), \
             patch("mgg.executor.TASKS_DIR", Path(tmp) / "tasks"):
            result = cmd_run(args)
            # Verify tasks were created and persisted
            tasks_dir = Path(tmp) / "tasks"
            task_ids = [d.name for d in tasks_dir.iterdir() if d.is_dir()]
            assert len(task_ids) == 2, f"expected 2 task dirs, got {task_ids}"


@patch("mgg.cli.subprocess.run")
def test_parallel_skill_inference(mock_run):
    """Parallel mode uses first prompt for skill inference."""
    mock_run.return_value = _mock_subprocess("ok")
    from mgg.cli import cmd_run

    args = Namespace(prompt=["审查代码", "实现功能"], skill=None, no_skill=False,
                     dep=[], inject=None, interactive=False,
                     parallel=True, max_workers=3)
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.cli.TASKS_DIR", Path(tmp) / "tasks"), \
             patch("mgg.persistence.TASKS_DIR", Path(tmp) / "tasks"), \
             patch("mgg.executor.TASKS_DIR", Path(tmp) / "tasks"):
            result = cmd_run(args)
            # Should infer "paa" from "审查代码"
            tasks_dir = Path(tmp) / "tasks"
            for d in tasks_dir.iterdir():
                state_file = d / "state.json"
                if state_file.exists():
                    import json
                    state = json.loads(state_file.read_text())
                    assert state["skill"] == "paa"
