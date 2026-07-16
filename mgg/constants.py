"""Shared path constants for mgg — no mgg-internal imports allowed."""

from pathlib import Path

MGG_DIR = Path(".mgg")
TASKS_DIR = MGG_DIR / "tasks"
SKILLS_DIR = Path.home() / ".claude" / "skills"
