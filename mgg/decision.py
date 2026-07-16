"""Decision channel: extract, validate, prompt, and inject human decisions."""

import json
import re
import sys

from mgg.persistence import _find_choice_label


def _extract_decision_from_output(text: str) -> dict | None:
    """Extract structured decision data from claude output.

    Detects:
    1. JSON block in code fence: any ``` or ```json with 'options'/'choices' array
    2. Markdown decision table: ## section with table containing options

    Returns {"question": str, "options": [{"id", "label", "pros", "cons"}]} or None.
    """
    candidates = []

    # Pattern 1: JSON block in code fence
    for match in re.finditer(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL):
        block = match.group(1).strip()
        try:
            data = json.loads(block)
            d = _validate_decision_json(data)
            if d:
                candidates.append(d)
        except json.JSONDecodeError:
            continue

    # Pattern 2: Markdown table with options
    d = _extract_markdown_decision_table(text)
    if d:
        candidates.append(d)

    if candidates:
        return candidates[0]
    return None


def _validate_decision_json(data: dict) -> dict | None:
    """Check if a parsed JSON dict looks like a decision structure."""
    if not isinstance(data, dict):
        return None
    opts = data.get("options") or data.get("choices") or data.get("alternatives")
    if not isinstance(opts, list) or len(opts) < 2:
        return None
    normalized = []
    for opt in opts:
        if isinstance(opt, str):
            normalized.append({"id": opt, "label": opt, "pros": "", "cons": ""})
        elif isinstance(opt, dict):
            oid = str(opt.get("id") or opt.get("name") or opt.get("option", ""))
            normalized.append({
                "id": oid,
                "label": str(opt.get("label") or opt.get("description", oid)),
                "pros": str(opt.get("pros") or opt.get("pro", "")),
                "cons": str(opt.get("cons") or opt.get("con", "")),
            })
    question = data.get("question") or data.get("prompt") or data.get("title", "请选择")
    return {"question": str(question), "options": normalized}


def _extract_markdown_decision_table(text: str) -> dict | None:
    """Try to extract from markdown table sections with option rows."""
    for match in re.finditer(
        r'(?:##|###|####)\s*(.*?)\n(.*?)(?=\n(?:##|###|####)|\Z)', text, re.DOTALL
    ):
        body = match.group(2)
        lines = body.strip().split("\n")
        options = []
        in_table = False
        question = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "问题" in line and "：" in line:
                question = line.split("：", 1)[-1]
            elif "问题" in line and ":" in line:
                question = line.split(":", 1)[-1].strip()
            if "|" in line and not line.startswith("|---"):
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if not in_table and len(cells) >= 2:
                    first = cells[0].lower()
                    if any(w in first for w in ["方案", "选项", "option", "choice", "id"]):
                        in_table = True
                        continue
                    else:
                        in_table = True
                if in_table and len(cells) >= 2:
                    aid = cells[0].split(":")[0].strip() if ":" in cells[0] else cells[0]
                    alabel = cells[0].split(":")[-1].strip() if ":" in cells[0] else cells[0]
                    options.append({
                        "id": aid,
                        "label": alabel,
                        "pros": cells[1] if len(cells) > 1 else "",
                        "cons": cells[2] if len(cells) > 2 else "",
                    })
        if len(options) >= 2:
            if not question:
                question = match.group(1).strip()
            return {"question": question, "options": options}
    return None


def _inject_decision_into_prompt(prompt: str, decision_data: dict | None) -> str:
    if not decision_data:
        return prompt
    d = decision_data.get("decision", {})
    return (
        f"{prompt}\n\n"
        f"[决策注入] {d.get('question', '前序决策')} "
        f"→ 选择: {decision_data.get('choice_label', decision_data.get('choice', '?'))}"
    )


def _prompt_human_for_decision(task_id: str, decision: dict) -> str | None:
    print(f"\n{'='*60}")
    print(f"  决策请求 — task {task_id}")
    print(f"{'='*60}")
    print(f"\n问题: {decision.get('question', '请选择')}\n")
    for opt in decision.get("options", []):
        label = f"{opt.get('id')}: {opt.get('label')}"
        print(f"  {label}")
        if opt.get("pros"):
            print(f"    优点: {opt['pros']}")
        if opt.get("cons"):
            print(f"    缺点: {opt['cons']}")
        print()
    print("输入选项 ID (或留空跳过):")
    try:
        choice = input("> ").strip()
        if not choice:
            print("[mgg] 决策跳过")
            return None
        return choice
    except (EOFError, KeyboardInterrupt):
        print("\n[mgg] 决策中断")
        return None
