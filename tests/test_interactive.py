"""Tests for interactive decision loop (_run_claude_with_session, _run_interactive_loop, --interactive flag)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.executor import _build_claude_args, _run_claude_with_session, _run_interactive_loop, MAX_INTERACTIVE_ROUNDS


# ── _build_claude_args with session ─────────────────────────────────────


def test_build_args_with_session():
    """Session mode adds --session flag instead of --no-session-persistence."""
    args = _build_claude_args("hello", "pdu", session_id="sess_abc")
    assert "--session" in args
    sess_idx = args.index("--session")
    assert args[sess_idx + 1] == "sess_abc"
    assert "--no-session-persistence" not in args


def test_build_args_without_session():
    """No session flag means --no-session-persistence."""
    args = _build_claude_args("hello", "pdu")
    assert "--no-session-persistence" in args
    assert "--session" not in args


def test_build_args_session_no_skill():
    """Session mode works without skill routing."""
    args = _build_claude_args("hello", None, session_id="sess_x")
    assert "--session" in args
    p_idx = args.index("-p")
    assert args[p_idx + 1] == "hello"


# ── _run_claude_with_session ────────────────────────────────────────────


@patch("mgg.executor.subprocess.run")
def test_run_claude_with_session_basic(mock_run):
    """Basic session run returns parsed result."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"type":"result","result":"done","session_id":"sess_1","total_cost_usd":0.05}\n',
        text=""
    )
    result = _run_claude_with_session("do something", "pdu")
    assert result["text"].strip() == "done"
    assert result["session_id"] == "sess_1"
    assert result["cost_usd"] == 0.05
    assert result["exit_code"] == 0


@patch("mgg.executor.subprocess.run")
def test_run_claude_with_session_inherits_id(mock_run):
    """Inherit session_id when claude doesn't return one."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"type":"result","result":"ok","total_cost_usd":0.01}\n',
        text=""
    )
    result = _run_claude_with_session("follow up", None, session_id="sess_1")
    assert result["session_id"] == "sess_1"


@patch("mgg.executor.subprocess.run")
def test_run_claude_with_session_failure(mock_run):
    """Failed subprocess returns non-zero exit code."""
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout='{"type":"result","result":"","errors":["timeout"],"total_cost_usd":null}\n',
        text=""
    )
    result = _run_claude_with_session("do thing", None)
    assert result["exit_code"] == 1
    assert "timeout" in result.get("errors", [])


# ── _run_interactive_loop (mocked subprocess) ────────────────────────────


def _mock_subprocess_result(text: str, session_id: str | None = "sess_1",
                            cost: float = 0.05):
    """Helper to create a mock subprocess result."""
    lines = []
    for line in text.strip().split("\n"):
        if line:
            lines.append(line)
    result_line = json.dumps({
        "type": "result", "result": text,
        "session_id": session_id, "total_cost_usd": cost
    })
    return MagicMock(returncode=0, stdout=result_line + "\n", text="")


@patch("mgg.executor.subprocess.run")
@patch("mgg.executor._prompt_human_for_decision", return_value=None)
def test_interactive_loop_no_decision(mock_prompt, mock_run):
    """No decision in output = single round, no human prompt."""
    mock_run.return_value = _mock_subprocess_result("task done")
    result = _run_interactive_loop("simple task", None)
    assert "task done" in result["text"]
    assert mock_prompt.call_count == 0
    assert result["session_id"] == "sess_1"


@patch("mgg.executor.subprocess.run")
@patch("mgg.executor._prompt_human_for_decision", return_value="A")
def test_interactive_loop_with_decision(mock_prompt, mock_run):
    """Decision in output triggers follow-up round."""
    responses = iter([
        _mock_subprocess_text(
            'analysis:\n```json\n{"question":"pick","options":[{"id":"A","label":"Option A"},{"id":"B","label":"Option B"}]}\n```'
        ),
        _mock_subprocess_text("round 2 done", cost=0.03),
    ])
    mock_run.side_effect = lambda *a, **kw: next(responses)
    result = _run_interactive_loop("compare options", None)
    assert mock_prompt.call_count == 1
    assert "round 2 done" in result["text"]


@patch("mgg.executor.subprocess.run")
@patch("mgg.executor._prompt_human_for_decision", return_value="A")
def test_interactive_loop_skips_decision(mock_prompt, mock_run):
    """User skipping decision breaks the loop."""
    mock_run.return_value = _mock_subprocess_text(
        '```json\n{"question":"pick","options":[{"id":"A","label":"A"},{"id":"B","label":"B"}]}\n```'
    )
    mock_prompt.return_value = None  # skip
    result = _run_interactive_loop("task", None)
    assert mock_prompt.call_count == 1


@patch("mgg.executor.subprocess.run")
@patch("mgg.executor._prompt_human_for_decision", return_value="A")
def test_interactive_loop_max_rounds(mock_prompt, mock_run):
    """Max rounds limit is enforced."""
    decision_text = '```json\n{"question":"again?","options":[{"id":"A","label":"A"},{"id":"B","label":"B"}]}\n```'

    def side_effect(*args, **kwargs):
        return _mock_subprocess_text(decision_text)

    mock_run.side_effect = side_effect
    result = _run_interactive_loop("loop task", None)
    assert mock_prompt.call_count == MAX_INTERACTIVE_ROUNDS - 1


@patch("mgg.executor.subprocess.run")
@patch("mgg.executor._prompt_human_for_decision", return_value="A")
def test_interactive_loop_skill_max_rounds(mock_prompt, mock_run):
    """Skill-declared max_interactive_rounds overrides default."""
    decision_text = '```json\n{"question":"again?","options":[{"id":"A","label":"A"},{"id":"B","label":"B"}]}\n```'

    def side_effect(*args, **kwargs):
        return _mock_subprocess_text(decision_text)

    mock_run.side_effect = side_effect
    # "paa" skill declares max_interactive_rounds: 10
    result = _run_interactive_loop("loop task", "paa")
    # With max_interactive_rounds=10, prompt is called 9 times (rounds-1)
    assert mock_prompt.call_count == 9


@patch("mgg.executor.subprocess.run")
@patch("mgg.executor._prompt_human_for_decision", return_value="A")
def test_interactive_loop_accumulates_cost(mock_prompt, mock_run):
    """Cost accumulates across rounds."""
    responses = iter([
        _mock_subprocess_text(
            '```json\n{"question":"pick","options":[{"id":"A","label":"A"},{"id":"B","label":"B"}]}\n```',
            cost=0.02
        ),
        _mock_subprocess_text("done", cost=0.03),
    ])
    mock_run.side_effect = lambda *a, **kw: next(responses)
    result = _run_interactive_loop("task", None)
    assert result["cost_usd"] == 0.05  # 0.02 + 0.03


@patch("mgg.executor.subprocess.run")
@patch("mgg.executor._prompt_human_for_decision", return_value="A")
def test_interactive_loop_merges_text(mock_prompt, mock_run):
    """Text from multiple rounds is merged."""
    responses = iter([
        _mock_subprocess_text("round1\n" + decision_json()),
        _mock_subprocess_text("round2 result"),
    ])
    mock_run.side_effect = lambda *a, **kw: next(responses)
    result = _run_interactive_loop("task", None)
    assert "round1" in result["text"]
    assert "round2" in result["text"]


# ── helpers ──────────────────────────────────────────────────────────────


def _mock_subprocess_text(text: str, session_id: str = "sess_1", cost: float = 0.02):
    """Create mock return with given text and JSON result line."""
    result_line = json.dumps({
        "type": "result", "result": text,
        "session_id": session_id, "total_cost_usd": cost
    })
    return MagicMock(returncode=0, stdout=result_line + "\n", text="")


def decision_json():
    return '```json\n{"question":"pick","options":[{"id":"A","label":"A"},{"id":"B","label":"B"}]}\n```'
