"""Integration tests for CLI commands (cmd_run, cmd_ls, cmd_status, cmd_resume, cmd_decide)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from argparse import Namespace
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import mgg
from mgg import (
    cmd_run, cmd_ls, cmd_status, cmd_resume, cmd_decide,
    _save_task, _load_task, _build_claude_args,
)


def _mock_stdout(text: str, cost: float = 0.05, sess: str = "sess_1"):
    """Create a mock subprocess result with JSON NDJSON stdout."""
    line = json.dumps({"type": "result", "result": text,
                        "session_id": sess, "total_cost_usd": cost})
    return MagicMock(returncode=0, stdout=line + "\n", text="")


def _make_fake_args(**overrides):
    """Create a Namespace with defaults for run command."""
    defaults = dict(prompt="test task", skill=None, no_skill=False,
                    dep=[], inject=None, interactive=False)
    defaults.update(overrides)
    return Namespace(**defaults)


# ── cmd_run ────────────────────────────────────────────────────────────

@patch("mgg.subprocess.run", return_value=_mock_stdout("done"))
def test_cmd_run_basic(mock_run):
    """Basic cmd_run completes successfully."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            state = cmd_run(_make_fake_args())
            assert state["status"] == "done"
            assert state["prompt"] == "test task"
            result_path = Path(tmp) / "tasks" / state["id"] / "result.md"
            assert result_path.read_text().strip() == "done"
        finally:
            mgg.TASKS_DIR = orig_dir


@patch("mgg.subprocess.run", return_value=_mock_stdout("done"))
def test_cmd_run_with_skill(mock_run):
    """Skill parameter is passed through."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            state = cmd_run(_make_fake_args(skill="pdu"))
            assert state["skill"] == "pdu"
        finally:
            mgg.TASKS_DIR = orig_dir


@patch("mgg.subprocess.run", return_value=_mock_stdout("done"))
def test_cmd_run_no_skill(mock_run):
    """no_skill=True skips skill inference."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            state = cmd_run(_make_fake_args(no_skill=True))
            assert state["skill"] is None
        finally:
            mgg.TASKS_DIR = orig_dir


@patch("mgg.subprocess.run")
def test_cmd_run_failed(mock_run):
    """Non-zero exit code marks task as failed."""
    mock_run.return_value = MagicMock(
        returncode=1, stdout='{"type":"result","result":"","errors":["fail"],"total_cost_usd":null}\n', text=""
    )
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            state = cmd_run(_make_fake_args())
            assert state["status"] == "failed"
        finally:
            mgg.TASKS_DIR = orig_dir


@patch("mgg.subprocess.run")
def test_cmd_run_interactive_flag(mock_run):
    """--interactive triggers interactive loop instead of batch."""
    mock_run.return_value = _mock_stdout("interactive done", sess="sess_i")
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            state = cmd_run(_make_fake_args(interactive=True))
            assert state["status"] == "done"
            # In test with mocked run, interactive loop does 1 round
            assert state["session_id"] is not None
            assert "interactive done" in (mgg.TASKS_DIR / state["id"] / "result.md").read_text()
        finally:
            mgg.TASKS_DIR = orig_dir


# ── cmd_status ─────────────────────────────────────────────────────────

def test_cmd_status_with_task_id(capsys):
    """Status with task ID prints state JSON and result."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            state = {"id": "t1", "prompt": "hi", "status": "done",
                     "skill": None, "created_at": "now"}
            _save_task(state)
            (mgg.TASKS_DIR / "t1" / "result.md").write_text("result text")
            cmd_status(Namespace(task_id="t1"))
            captured = capsys.readouterr()
            assert "t1" in captured.out
            assert "result text" in captured.out
        finally:
            mgg.TASKS_DIR = orig_dir


def test_cmd_status_list_tasks(capsys):
    """Status without task ID lists all tasks."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            for tid in ("ta", "tb"):
                _save_task({"id": tid, "prompt": f"task {tid}",
                            "status": "done", "skill": "pdu",
                            "created_at": f"2026-01-01T00:00:{'0' if tid=='ta' else '1'}Z",
                            "cost_usd": 0.05})
            cmd_status(Namespace(task_id=None))
            captured = capsys.readouterr()
            assert "ta" in captured.out
            assert "tb" in captured.out
        finally:
            mgg.TASKS_DIR = orig_dir


# ── cmd_ls ─────────────────────────────────────────────────────────────

def test_cmd_ls_no_skills(capsys):
    """ls with no skills prints no-skills message."""
    with tempfile.TemporaryDirectory() as tmp:
        orig = mgg.SKILLS_DIR
        try:
            mgg.SKILLS_DIR = Path(tmp)
            cmd_ls(None)
            captured = capsys.readouterr()
            assert "no skills" in captured.out
        finally:
            mgg.SKILLS_DIR = orig


def test_cmd_ls_with_multiple_skills(capsys):
    """ls lists multiple skills."""
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("skill-a", "skill-b"):
            d = Path(tmp) / name
            d.mkdir()
            (d / "SKILL.md").write_text('---\ndescription: "desc"\n---\n')
        orig = mgg.SKILLS_DIR
        try:
            mgg.SKILLS_DIR = Path(tmp)
            cmd_ls(None)
            captured = capsys.readouterr()
            assert "skill-a" in captured.out
            assert "skill-b" in captured.out
        finally:
            mgg.SKILLS_DIR = orig


# ── cmd_resume ─────────────────────────────────────────────────────────

@patch("mgg.subprocess.run", return_value=_mock_stdout("resumed"))
def test_cmd_resume_basic(mock_run):
    """Resume re-runs a failed task with same prompt."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            _save_task({"id": "r1", "prompt": "retry", "skill": "pdu",
                        "status": "failed", "dependencies": [],
                        "inject": None})
            state = cmd_resume(Namespace(task_id="r1"))
            assert state["status"] == "done"
        finally:
            mgg.TASKS_DIR = orig_dir


# ── cmd_decide ─────────────────────────────────────────────────────────

@patch("mgg.subprocess.run")
def test_cmd_decide_basic(mock_run, capsys):
    """Decide records a choice for a completed task."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            _save_task({"id": "d1", "prompt": "pick", "status": "done",
                        "skill": None})

            # result.md with decision block
            result_text = '```json\n{"question":"pick?","options":[{"id":"X","label":"X"},{"id":"Y","label":"Y"}]}\n```'
            (mgg.TASKS_DIR / "d1" / "result.md").write_text(result_text)

            cmd_decide(Namespace(task_id="d1", choice="X"))
            captured = capsys.readouterr()
            assert "X" in captured.out

            # verify decision.json was written
            dec_path = mgg.TASKS_DIR / "d1" / "decision.json"
            assert dec_path.exists()
            dec = json.loads(dec_path.read_text())
            assert dec["choice"] == "X"
        finally:
            mgg.TASKS_DIR = orig_dir


# ── argparse / main ──────────────────────────────────────────────────

def test_argparse_run_defaults():
    """Run command parses default args correctly."""
    args = mgg.parser.parse_args(["run", "test prompt"])
    assert args.command == "run"
    assert args.prompt == "test prompt"
    assert args.interactive is False
    assert args.dep == []


def test_argparse_run_interactive():
    """--interactive flag is parsed correctly."""
    args = mgg.parser.parse_args(["run", "-i", "interactive task"])
    assert args.interactive is True


def test_argparse_run_with_all_flags():
    """All run flags parse correctly."""
    args = mgg.parser.parse_args(
        ["run", "task", "--skill", "pdu", "--interactive", "--dep", "a", "b", "--inject", "c"]
    )
    assert args.skill == "pdu"
    assert args.interactive is True
    assert args.dep == ["a", "b"]
    assert args.inject == "c"


def test_argparse_status():
    """Status command parses optional task_id."""
    args = mgg.parser.parse_args(["status"])
    assert args.command == "status"
    assert args.task_id is None

    args = mgg.parser.parse_args(["status", "abc123"])
    assert args.task_id == "abc123"


def test_argparse_ls():
    """Ls command has no arguments."""
    args = mgg.parser.parse_args(["ls"])
    assert args.command == "ls"


def test_argparse_resume():
    """Resume command requires task_id."""
    args = mgg.parser.parse_args(["resume", "abc123"])
    assert args.task_id == "abc123"


def test_argparse_decide():
    """Decide command requires task_id and choice."""
    args = mgg.parser.parse_args(["decide", "abc123", "A"])
    assert args.task_id == "abc123"
    assert args.choice == "A"
