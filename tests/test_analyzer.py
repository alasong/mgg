"""Tests for _preflight_analyze (subprocess mock)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.analyzer import _preflight_analyze


def _mock_claude_response(text: str, cost: float = 0.01):
    """Mock a claude subprocess returning NDJSON with a result."""
    line = json.dumps({"type": "result", "result": text,
                        "session_id": "preflight", "total_cost_usd": cost})
    return MagicMock(returncode=0, stdout=line + "\n", stderr="")


def _mock_ndjson(decision_list_json: str):
    """Wrap a decision JSON list into NDJSON subprocess result."""
    return _mock_claude_response(decision_list_json)


def test_analyze_returns_decision_list():
    """Normal case: Claude returns decision points, parsed correctly."""
    mock_json = json.dumps([
        {"question": "选择数据库", "options": ["Postgres", "SQLite"]},
        {"question": "认证方式", "options": ["JWT", "Session"]},
    ])
    mock_run = MagicMock(return_value=_mock_claude_response(mock_json))
    with patch("mgg.analyzer.subprocess.run", mock_run):
        result = _preflight_analyze("实现登录模块")
        assert len(result) == 2
        assert result[0]["question"] == "选择数据库"
        assert result[1]["options"][0]["id"] == "JWT"


def test_analyze_no_decisions():
    """Claude returns no decisions (empty list or no decision schema)."""
    mock_run = MagicMock(return_value=_mock_claude_response("[]"))
    with patch("mgg.analyzer.subprocess.run", mock_run):
        result = _preflight_analyze("简单任务")
        assert result == []


def test_analyze_invalid_json():
    """Invalid JSON from Claude returns empty list without crashing."""
    mock_run = MagicMock(return_value=_mock_claude_response("{bad json}"))
    with patch("mgg.analyzer.subprocess.run", mock_run):
        result = _preflight_analyze("测试")
        assert result == []


def test_analyze_subprocess_fails():
    """Subprocess failure returns empty list."""
    mock_run = MagicMock(return_value=MagicMock(returncode=1, stdout="", stderr="error"))
    with patch("mgg.analyzer.subprocess.run", mock_run):
        result = _preflight_analyze("测试")
        assert result == []


# ── Three-layer preflight ──────────────────────────────────────────


def test_analyze_declarative_decisions():
    """Layer 1: Declarative decisions are parsed correctly."""
    # Test _parse_skill_meta with YAML frontmatter directly
    from mgg.router import _parse_skill_meta
    from mgg.analyzer import _normalize_declarative_decisions

    skill_md = ("---\nname: paa\ndescription: test\ndecisions:\n"
                '  - question: "审查模式"\n'
                "    options:\n"
                '      - "默认 TDD"\n'
                '      - "纯分析 --analysis"\n'
                '  - question: "轮次上限"\n'
                "    options:\n"
                '      - id: "3"\n        label: "3 轮"\n'
                '      - id: "5"\n        label: "5 轮"\n'
                "---\n")

    with tempfile.TemporaryDirectory() as tmp:
        md_path = Path(tmp) / "SKILL.md"
        md_path.write_text(skill_md)
        meta = _parse_skill_meta(md_path)
        assert meta.get("decisions"), "should have decisions from YAML"
        assert len(meta["decisions"]) == 2

        result = _normalize_declarative_decisions(meta["decisions"])
        assert len(result) == 2
        assert result[0]["question"] == "审查模式"
        assert result[1]["options"][0]["id"] == "3"


def test_analyze_skill_without_declarations_falls_to_llm():
    """Layer 2: Skill without declarative decisions falls back to LLM with skill context."""
    mock_json = json.dumps([
        {"question": "并行数?", "options": [{"id": "2", "label": "2"}, {"id": "4", "label": "4"}]},
    ])
    mock_run = MagicMock(return_value=_mock_ndjson(mock_json))

    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "pdu"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: pdu\ndescription: parallel skill\n---\n\nPDU content")

        with patch("mgg.analyzer.SKILLS_DIR", Path(tmp)), \
             patch("mgg.analyzer.subprocess.run", mock_run):
            result = _preflight_analyze("跑多个任务", skill_name="pdu")
            assert len(result) == 1
            assert "并行数" in result[0]["question"]


def test_analyze_no_skill_falls_to_generic():
    """Layer 3: No skill name falls to generic task decomposition."""
    mock_json = json.dumps([
        {"question": "用什么数据库?", "options": [{"id": "A", "label": "Postgres"}, {"id": "B", "label": "SQLite"}]},
    ])
    mock_run = MagicMock(return_value=_mock_ndjson(mock_json))
    with patch("mgg.analyzer.subprocess.run", mock_run):
        result = _preflight_analyze("实现登录模块")
        assert len(result) == 1
        assert "数据库" in result[0]["question"]


def test_analyze_unknown_skill_falls_to_generic():
    """Unknown skill name falls to generic task decomposition."""
    mock_json = json.dumps([
        {"question": "测试?", "options": [{"id": "A", "label": "是"}, {"id": "B", "label": "否"}]},
    ])
    mock_run = MagicMock(return_value=_mock_ndjson(mock_json))
    with patch("mgg.analyzer.subprocess.run", mock_run):
        result = _preflight_analyze("测试", skill_name="nonexistent_skill")
        assert len(result) == 1
