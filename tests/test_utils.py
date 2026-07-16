"""Tests for mgg utility functions (_build_claude_args, _now, _discover_skills, _parse_skill_meta)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg import _build_claude_args, _now, _discover_skills, _parse_skill_meta, cmd_ls, cmd_status


def test_now_iso_format():
    """_now() returns ISO 8601 formatted datetime."""
    now = _now()
    # Should contain 'T' separator and timezone info
    assert "T" in now
    assert now.endswith("+00:00") or now.endswith("Z") or "+" in now


def test_build_claude_args_with_skill():
    """Build args with skill prefix."""
    args = _build_claude_args("implement feature X", "paa")
    assert args[0] == "claude"
    assert "-p" in args
    p_idx = args.index("-p")
    # prompt should be /skill prompt
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
    # Check values
    fmt_idx = args.index("--output-format")
    assert args[fmt_idx + 1] == "json"
    perm_idx = args.index("--permission-mode")
    assert args[perm_idx + 1] == "auto"


def test_discover_skills_no_dir():
    """No skills directory returns empty list."""
    with tempfile.TemporaryDirectory() as tmp:
        skills_dir = Path(tmp) / "nonexistent"
        import mgg
        original = mgg.SKILLS_DIR
        try:
            mgg.SKILLS_DIR = skills_dir
            skills = _discover_skills()
            assert skills == []
        finally:
            mgg.SKILLS_DIR = original


def test_discover_skills_empty_dir():
    """Empty skills directory returns empty list."""
    with tempfile.TemporaryDirectory() as tmp:
        import mgg
        original = mgg.SKILLS_DIR
        try:
            mgg.SKILLS_DIR = Path(tmp)
            skills = _discover_skills()
            assert skills == []
        finally:
            mgg.SKILLS_DIR = original


def test_discover_skills_with_valid_skill():
    """Directory with SKILL.md returns skill with parsed metadata."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            '---\ndescription: "Test skill description"\n---\n\n# Content'
        )
        import mgg
        original = mgg.SKILLS_DIR
        try:
            mgg.SKILLS_DIR = Path(tmp)
            skills = _discover_skills()
            assert len(skills) == 1
            assert skills[0]["name"] == "test-skill"
            assert skills[0]["description"] == "Test skill description"
        finally:
            mgg.SKILLS_DIR = original


def test_discover_skills_ignores_dirs_without_skill_md():
    """Directories without SKILL.md are skipped."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "no-skill"
        skill_dir.mkdir()
        import mgg
        original = mgg.SKILLS_DIR
        try:
            mgg.SKILLS_DIR = Path(tmp)
            skills = _discover_skills()
            assert skills == []
        finally:
            mgg.SKILLS_DIR = original


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


def test_cmd_status_no_tasks(capsys):
    """status command with no tasks prints message."""
    with tempfile.TemporaryDirectory() as tmp:
        import mgg
        orig = mgg.TASKS_DIR
        try:
            mgg.TASKS_DIR = Path(tmp) / "tasks"
            class FakeArgs:
                task_id = None
            cmd_status(FakeArgs())
            captured = capsys.readouterr()
            assert "no tasks" in captured.out
        finally:
            mgg.TASKS_DIR = orig


def test_cmd_ls_with_skills(capsys):
    """ls command prints skill names."""
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text('---\ndescription: "desc"\n---\n')
        import mgg
        orig = mgg.SKILLS_DIR
        try:
            mgg.SKILLS_DIR = Path(tmp)
            cmd_ls(None)
            captured = capsys.readouterr()
            assert "test-skill" in captured.out
        finally:
            mgg.SKILLS_DIR = orig
