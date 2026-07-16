"""Tests for Claude output parsing (JSON NDJSON + plain text fallback)."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.executor import _parse_claude_output


def test_parse_simple_result():
    """Parse a single result JSON line."""
    stdout = '{"type":"result","result":"done","total_cost_usd":0.05,"session_id":"sess_1"}\n'
    parsed = _parse_claude_output(stdout)
    assert parsed["text"].strip() == "done"
    assert parsed["cost_usd"] == 0.05
    assert parsed["session_id"] == "sess_1"
    assert parsed["errors"] == []


def test_parse_result_with_text():
    """Parse result with text content."""
    stdout = '{"type":"result","result":"task completed\\nall good","total_cost_usd":0.1}\n'
    parsed = _parse_claude_output(stdout)
    assert "task completed" in parsed["text"]
    assert "all good" in parsed["text"]


def test_parse_result_with_errors():
    """Parse result with error messages."""
    stdout = '{"type":"result","result":"partial","errors":["timeout on step 2"],"total_cost_usd":null}\n'
    parsed = _parse_claude_output(stdout)
    assert parsed["errors"] == ["timeout on step 2"]
    assert parsed["cost_usd"] is None


def test_parse_plain_text_no_json():
    """Fallback: non-JSON lines accumulated as text."""
    stdout = "starting task...\nworking...\ndone."
    parsed = _parse_claude_output(stdout)
    assert "starting task..." in parsed["text"]
    assert parsed["cost_usd"] is None
    assert parsed["session_id"] is None


def test_parse_mixed_json_and_text():
    """Mix of non-JSON progress lines and final JSON result."""
    stdout = (
        "computing...\n"
        '{"type":"progress","pct":50}\n'
        "still working...\n"
        '{"type":"result","result":"finished","total_cost_usd":0.03}\n'
    )
    parsed = _parse_claude_output(stdout)
    assert "computing..." in parsed["text"]
    assert "still working..." in parsed["text"]
    assert "finished" in parsed["text"]
    assert parsed["cost_usd"] == 0.03


def test_parse_empty_output():
    """Empty output returns default structure."""
    parsed = _parse_claude_output("")
    assert parsed["text"] == ""
    assert parsed["errors"] == []
    assert parsed["cost_usd"] is None
    assert parsed["session_id"] is None


def test_parse_json_without_type_field():
    """JSON lines without 'type:result' are protocol events, silently dropped."""
    stdout = '{"some":"data","value":42}\n'
    parsed = _parse_claude_output(stdout)
    assert parsed["text"] == ""
    assert parsed["cost_usd"] is None


def test_parse_result_without_text_content():
    """JSON result line with no 'result' field returns empty text."""
    stdout = '{"type":"result","total_cost_usd":0.01}\n'
    parsed = _parse_claude_output(stdout)
    assert parsed["text"] == ""
    assert parsed["cost_usd"] == 0.01


def test_parse_multiple_result_lines():
    """Only the last result line's text should be kept."""
    stdout = (
        '{"type":"result","result":"step1","total_cost_usd":0.01}\n'
        '{"type":"result","result":"step2","total_cost_usd":0.02}\n'
    )
    parsed = _parse_claude_output(stdout)
    # Each result line appends to text
    assert "step1" in parsed["text"]
    assert "step2" in parsed["text"]
    assert parsed["cost_usd"] == 0.02  # last wins
