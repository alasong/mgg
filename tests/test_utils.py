"""Tests for mgg utility functions (_build_claude_args, _now, _discover_skills, _parse_skill_meta)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg.executor import _build_claude_args
from mgg.utils import _now
from mgg.router import _discover_skills, _parse_skill_meta
from mgg.cli import cmd_ls, cmd_status


def test_now_iso_format():
    """_now() returns ISO 8601 formatted datetime."""
    now = _now()
    assert "T" in now
    assert now.endswith("+00:00") or now.endswith("Z") or "+" in now


def test_build_claude_args_with_skill():
    """Build args with skill prefix."""
    args = _build_claude_args("implement feature X", "paa")
    assert args[0] == "claude"
    assert "-p" in args
    p_idx = args.index("-p")
    assert args[p_idx + 1] == "/paa implement feature X"


def test_build_claude_args_without_skill():
    """Build args without skill passes prompt directly."""
    args = _build_claude_args("hello world", None)
    assert "-p" in args
    p_idx = args.index("-p")
    assert args[p_idx + 1] == "hello world"


def test_build_claude_args_has_flags():
    """Output format and permission flags are always present."""
    args = _build_claude_args("test", "pdu")
    assert "--output-format" in args
    assert "--permission-mode" in args
    assert "--no-session-persistence" in args
    fmt_idx = args.index("--output-format")
    assert args[fmt_idx + 1] == "json"
    perm_idx = args.index("--permission-mode")
    assert args[perm_idx + 1] == "auto"


def test_discover_skills_no_dir():
    """No skills directory returns empty list."""
    with tempfile.TemporaryDirectory() as tmp:
        skills_dir = Path(tmp) / "nonexistent"
        with patch("mgg.router.SKILLS_DIR", skills_dir):
            skills = _discover_skills()
            assert skills == []


def test_discover_skills_empty_dir():
    """Empty skills directory returns empty list."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.router.SKILLS_DIR", Path(tmp)):
            skills = _discover_skills()
            assert skills == []


def test_discover_skills_with_valid_skill():
    """Directory with SKILL.md returns skill with parsed metadata."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\ndescription: "Test skill description"\n---\n\n# Content'
        )
        with patch("mgg.router.SKILLS_DIR", Path(tmp)):
            skills = _discover_skills()
            assert len(skills) == 1
            assert skills[0]["name"] == "test-skill"
            assert skills[0]["description"] == "Test skill description"


def test_discover_skills_ignores_dirs_without_skill_md():
    """Directories without SKILL.md are skipped."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "no-skill"
        skill_dir.mkdir()
        with patch("mgg.router.SKILLS_DIR", Path(tmp)):
            skills = _discover_skills()
            assert skills == []


def test_parse_skill_meta_no_frontmatter():
    """SKILL.md without frontmatter returns default metadata."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "SKILL.md"
        path.write_text("# Just content\nno frontmatter")
        meta = _parse_skill_meta(path)
        assert meta["description"] == ""


def test_parse_skill_meta_with_frontmatter():
    """SKILL.md with frontmatter parses description field."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "SKILL.md"
        path.write_text(
            '---\ndescription: "A skill for testing"\nversion: "1.0"\n---\n\nContent'
        )
        meta = _parse_skill_meta(path)
        assert "description" in meta
        assert meta["description"] == "A skill for testing"


def test_parse_skill_meta_routing_and_config():
    """SKILL.md with routing, max_workers, max_interactive_rounds parses correctly."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "SKILL.md"
        path.write_text(
            "---\n"
            'description: "routing skill"\n'
            "routing:\n"
            "  keywords: [\"审查\", \"review\"]\n"
            "max_workers: 5\n"
            "max_interactive_rounds: 10\n"
            "---\n\nContent"
        )
        meta = _parse_skill_meta(path)
        assert meta["routing"]["keywords"] == ["审查", "review"]
        assert meta["max_workers"] == 5
        assert meta["max_interactive_rounds"] == 10


def test_parse_skill_meta_unknown_keys_ignored():
    """Unknown frontmatter keys are not included in parsed meta."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "SKILL.md"
        path.write_text(
            "---\n"
            'description: "test"\n'
            "unknown_key: true\n"
            "---\n\nContent"
        )
        meta = _parse_skill_meta(path)
        assert "unknown_key" not in meta


def test_cmd_status_no_tasks(capsys):
    """status command with no tasks prints message."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch("mgg.cli.TASKS_DIR", Path(tmp) / "tasks"):
            class FakeArgs:
                task_id = None
            cmd_status(FakeArgs())
            captured = capsys.readouterr()
            assert "no tasks" in captured.out


def test_cmd_ls_with_skills(capsys):
    """ls command prints skill names."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text('---\ndescription: "desc"\n---\n')
        with patch("mgg.router.SKILLS_DIR", Path(tmp)):
            cmd_ls(None)
            captured = capsys.readouterr()
            assert "test-skill" in captured.out
