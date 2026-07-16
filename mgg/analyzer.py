"""Preflight decision analysis: three-layer approach.

Layer 1 (Declarative): If the target skill declares `decisions:` in its SKILL.md
  frontmatter, return those directly — zero LLM calls.

Layer 2 (Skill-aware): If a skill is inferred but has no `decisions:` field,
  pass the SKILL.md content to Claude and ask it to identify decision points
  specific to that skill's flow.

Layer 3 (Generic): If no skill is used, decompose the task into steps and
  identify decisions at each step.
"""

import json
import subprocess
import sys

from mgg.constants import SKILLS_DIR, TASKS_DIR


def _preflight_analyze(prompt: str, skill_name: str | None = None) -> list[dict]:
    """Analyze prompt to find decision points.

    Three layers, tried in order:
    1. If skill_name has declarative `decisions:` in SKILL.md → return directly
    2. If skill_name exists → pass SKILL.md to Claude for analysis
    3. If no skill → decompose task steps generically
    """
    if skill_name:
        skill_dir = SKILLS_DIR / skill_name
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            # Layer 1: Check for declarative decisions
            from mgg.router import _parse_skill_meta
            meta = _parse_skill_meta(skill_md)
            if meta.get("decisions"):
                return _normalize_declarative_decisions(meta["decisions"])

            # Layer 2: Skill-aware LLM analysis
            skill_content = skill_md.read_text()[:4000]  # first 4K chars
            return _analyze_with_skill_context(prompt, skill_name, skill_content)

    # Layer 3: Generic task decomposition
    return _analyze_generic(prompt)


def _normalize_declarative_decisions(decisions: list) -> list[dict]:
    """Normalize YAML-parsed declarative decisions to internal format."""
    normalized = []
    for d in decisions:
        if not isinstance(d, dict):
            continue
        question = d.get("question", "请选择")
        raw_opts = d.get("options", [])
        if not isinstance(raw_opts, list) or len(raw_opts) < 2:
            continue
        opts = []
        for o in raw_opts:
            if isinstance(o, str):
                opts.append({"id": o, "label": o, "pros": "", "cons": ""})
            elif isinstance(o, dict):
                oid = str(o.get("id") or o.get("option") or "")
                opts.append({
                    "id": oid,
                    "label": str(o.get("label") or o.get("description", oid)),
                    "pros": str(o.get("pros", "")),
                    "cons": str(o.get("cons", "")),
                })
        if len(opts) >= 2:
            normalized.append({"question": str(question), "options": opts})
    return normalized


def _analyze_with_skill_context(prompt: str, skill_name: str, skill_content: str) -> list[dict]:
    """Layer 2: Pass SKILL.md context to Claude for decision analysis."""
    system_prompt = (
        "你正在为一个使用技能的分析任务做决策预分析。\n\n"
        f"技能「{skill_name}」的描述如下：\n---\n{skill_content}\n---\n\n"
        "基于该技能的能力和以下用户任务，识别需要人类确认的关键决策点。\n"
        "只输出与技能流程相关的、需要人类选择的决策点，不要编造无关选项。\n"
        "如果没有需要决策的选项，输出空数组 []。\n\n"
        "输出格式（JSON 数组）：\n"
        '[{"question": "决策问题", "options": [{"id": "A", "label": "选项"}, ...]}, ...]'
    )
    return _call_claude_preflight(system_prompt, prompt)


def _analyze_generic(prompt: str) -> list[dict]:
    """Layer 3: Generic task-step decomposition."""
    system_prompt = (
        "将以下任务分解为逻辑步骤序列。针对每个步骤，识别用户需要做选择的决策点。\n\n"
        "只输出一个 JSON 数组，每个元素包含 question（决策问题）和 options（选项列表）。\n"
        "如果没有需要决策的选项，输出空数组 []。\n\n"
        "输出格式：\n"
        '[{"question": "决策问题", "options": [{"id": "A", "label": "选项"}, ...]}, ...]'
    )
    return _call_claude_preflight(system_prompt, prompt)


_PREFLIGHT_TIMEOUT = 30


def _call_claude_preflight(system_prompt: str, prompt: str) -> list[dict]:
    """Call Claude for preflight analysis."""
    full_prompt = f"{system_prompt}\n\n任务: {prompt}"
    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt,
             "--output-format", "json",
             "--permission-mode", "auto",
             "--no-session-persistence"],
            capture_output=True, text=True, timeout=_PREFLIGHT_TIMEOUT,
        )
        if result.returncode != 0:
            return []
        return _parse_preflight_output(result.stdout)
    except (subprocess.TimeoutExpired, OSError):
        return []


def _parse_preflight_output(stdout: str) -> list[dict]:
    """Parse NDJSON output from preflight Claude call."""
    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "result":
            text = obj.get("result", "").strip()
            if not text:
                return []
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                return []
            if not isinstance(raw, list):
                return []
            normalized = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                question = item.get("question", "请选择")
                opts = item.get("options") or item.get("choices") or []
                if not isinstance(opts, list) or len(opts) < 2:
                    continue
                normalized_opts = []
                for opt in opts:
                    if isinstance(opt, str):
                        normalized_opts.append({"id": opt, "label": opt, "pros": "", "cons": ""})
                    elif isinstance(opt, dict):
                        oid = str(opt.get("id") or opt.get("name") or "")
                        normalized_opts.append({
                            "id": oid,
                            "label": str(opt.get("label") or opt.get("description", oid)),
                            "pros": str(opt.get("pros") or opt.get("pro", "")),
                            "cons": str(opt.get("cons") or opt.get("con", "")),
                        })
                if len(normalized_opts) >= 2:
                    normalized.append({"question": str(question), "options": normalized_opts})
            return normalized
    return []


def _batch_prompt_human(decisions: list[dict]) -> dict[str, str]:
    """Present multiple decisions to user, collect choices.

    Returns dict of {question: choice_id}. Only decisions where user
    made a choice are included (skipped ones excluded).
    """
    if not decisions:
        return {}

    print(f"\n{'='*60}")
    print("  预分析 — 执行前需要确认的决策")
    print(f"{'='*60}\n")

    choices = {}
    for i, decision in enumerate(decisions, 1):
        question = decision.get("question", "请选择")
        opts = decision.get("options", [])
        print(f"[{i}/{len(decisions)}] 问题: {question}")
        for opt in opts:
            label = f"  {opt.get('id')}: {opt.get('label')}"
            print(label)
            if opt.get("pros"):
                print(f"    优点: {opt['pros']}")
            if opt.get("cons"):
                print(f"    缺点: {opt['cons']}")
            print()

        try:
            choice = input(f"输入选项 ID (或留空跳过): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            choice = ""

        if choice:
            choices[question] = choice
            print(f"  → 已选择: {choice}\n")
        else:
            print(f"  → 跳过\n")

    return choices


def _build_injection_text(decisions: list[dict], choices: dict[str, str]) -> str:
    """Build injection text from decisions and user choices to prepend to prompt."""
    if not choices:
        return "\n\n[已确认决策]\n无\n"

    lines = ["", "[已确认决策]"]
    for d in decisions:
        q = d["question"]
        if q not in choices:
            continue
        chosen_id = choices[q]
        label = chosen_id
        for opt in d["options"]:
            if opt.get("id") == chosen_id:
                label = f"{chosen_id}: {opt.get('label', chosen_id)}"
                break
        lines.append(f"- {q} → {label}")

    lines.append("以上决策已确认，请按此执行。\n")
    return "\n".join(lines)
