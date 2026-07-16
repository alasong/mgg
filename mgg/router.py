"""Skill routing and discovery for mgg."""

from pathlib import Path

import yaml

from mgg.constants import SKILLS_DIR


def _discover_skills() -> list[dict]:
    if not SKILLS_DIR.exists():
        return []
    skills = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            meta = _parse_skill_meta(d / "SKILL.md")
            meta["name"] = d.name
            skills.append(meta)
    return skills


def _parse_skill_meta(path: Path) -> dict:
    """Parse YAML frontmatter from SKILL.md."""
    text = path.read_text()
    meta = {"description": "", "decisions": []}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            try:
                front = yaml.safe_load(text[3:end])
                if isinstance(front, dict):
                    # Keep only known keys to avoid leaking arbitrary frontmatter
                    for key in ("description", "decisions", "argument-hint", "capabilities",
                                "routing", "max_workers", "max_interactive_rounds",
                                "preflight_timeout", "post_execution_decisions"):
                        if key in front:
                            meta[key] = front[key]
            except yaml.YAMLError:
                pass
    return meta


def _infer_skill(prompt: str) -> str:
    prompt_lower = prompt.lower()
    for skill in _discover_skills():
        keywords = skill.get("routing", {}).get("keywords", [])
        if any(kw.lower() in prompt_lower for kw in keywords):
            return skill["name"]
    return "pdu"
