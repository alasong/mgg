#!/usr/bin/env python3
"""mgg — CLI project management tool: spawns isolated Claude Code subprocesses per task."""

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

MGG_DIR = Path(".mgg")
TASKS_DIR = MGG_DIR / "tasks"
SKILLS_DIR = Path.home() / ".claude" / "skills"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_task(task_id: str) -> dict:
    path = TASKS_DIR / task_id / "state.json"
    if not path.exists():
        die(f"task not found: {task_id}")
    return json.loads(path.read_text())


def _save_task(state: dict):
    task_dir = TASKS_DIR / state["id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))


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
    text = path.read_text()
    meta = {"description": ""}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            for line in text[3:end].strip().split("\n"):
                for key in ("description",):
                    prefix = f"{key}: "
                    if line.strip().startswith(prefix):
                        meta[key] = line.strip()[len(prefix):].strip('"')
    return meta


def die(msg: str, code: int = 1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


# ── run ──────────────────────────────────────────────────────────────

def cmd_run(args):
    prompt = args.prompt
    skill = args.skill if args.skill else (None if getattr(args, "no_skill", False) else _infer_skill(prompt))
    interactive = getattr(args, "interactive", False)
    task_id = uuid.uuid4().hex[:12]

    # --inject: load decision from referenced task and inject into prompt
    inject_id = getattr(args, "inject", None)
    decision_data = None
    if inject_id:
        dep_dir = TASKS_DIR / inject_id
        decision_data = _load_decision(dep_dir)
        if decision_data:
            prompt = _inject_decision_into_prompt(prompt, decision_data)
            print(f"[mgg] injected decision from task {inject_id}")
        else:
            print(f"[mgg] warning: no decision found in task {inject_id}")

    state = {
        "id": task_id,
        "prompt": prompt,
        "skill": skill,
        "status": "running",
        "created_at": _now(),
        "finished_at": None,
        "exit_code": None,
        "cost_usd": None,
        "session_id": None,
        "error": None,
        "dependencies": args.dep or [],
        "inject": inject_id,
    }
    _save_task(state)

    if args.dep:
        _wait_dependencies(args.dep)

    claude_args = _build_claude_args(prompt, skill)
    print(f"[mgg] task {task_id} — skill={skill} ({'interactive' if interactive else 'batch'})")
    sys.stdout.flush()

    if interactive:
        parsed = _run_interactive_loop(prompt, skill)
        state["exit_code"] = 0
        if parsed.get("errors"):
            state["exit_code"] = 1
    else:
        result = subprocess.run(claude_args, capture_output=True, text=True)
        parsed = _parse_claude_output(result.stdout)
        state["exit_code"] = result.returncode

    state["cost_usd"] = parsed.get("cost_usd")
    state["session_id"] = parsed.get("session_id")

    result_path = TASKS_DIR / task_id / "result.md"
    result_text = parsed.get("text", "").strip()
    if result_text:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(result_text)

    exit_code = state["exit_code"]
    if exit_code == 0 and not parsed.get("errors"):
        state["status"] = "done"
    else:
        state["status"] = "failed"
        errs = parsed.get("errors", [])
        state["error"] = errs[0] if errs else f"exit code {exit_code}"

    state["finished_at"] = _now()
    _save_task(state)

    # Post-hoc decision extraction (batch mode only — interactive handles inline)
    if not interactive and state["status"] == "done":
        decision = _extract_decision_from_output(result_text)
        if decision:
            choice = _prompt_human_for_decision(task_id, decision)
            if choice:
                _save_decision(TASKS_DIR / task_id, decision, choice)
                state["decision"] = choice
                _save_task(state)

    # print result
    if result_text:
        print(f"\n── result ──────────────────────────────────")
        print(result_text[:2000])
        if len(result_text) > 2000:
            print(f"\n... (truncated, full at {result_path})")
        print()

    _print_status_line(state)
    return state


def _build_claude_args(prompt: str, skill: str | None, session_id: str | None = None) -> list[str]:
    if skill:
        full_prompt = f"/{skill} {prompt}"
    else:
        full_prompt = prompt

    args = ["claude", "-p", full_prompt,
            "--output-format", "json",
            "--permission-mode", "auto"]
    if session_id:
        args.extend(["--session", session_id])
    else:
        args.append("--no-session-persistence")
    return args


def _parse_claude_output(stdout: str) -> dict:
    result = {"cost_usd": None, "session_id": None, "errors": [], "text": ""}
    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            result["text"] += line + "\n"
            continue
        if obj.get("type") == "result":
            result["cost_usd"] = obj.get("total_cost_usd")
            result["session_id"] = obj.get("session_id")
            result["errors"] = obj.get("errors") or []
            if obj.get("result"):
                result["text"] += obj["result"] + "\n"
    return result


def _infer_skill(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if any(w in prompt_lower for w in ["审查", "review", "audit"]):
        return "paa"
    if any(w in prompt_lower for w in ["并行", "parallel", "多个任务", "多个模块"]):
        return "pdu"
    if any(w in prompt_lower for w in ["tdd", "测试驱动"]):
        return "ulw"
    if any(w in prompt_lower for w in ["流程", "多步", "pipeline"]):
        return "pfs"
    if any(w in prompt_lower for w in ["分析", "research", "调研"]):
        return "pff"
    return "pdu"


# ── interactive loop ────────────────────────────────────────────────────

MAX_INTERACTIVE_ROUNDS = 5


def _run_claude_with_session(prompt: str, skill: str | None,
                             session_id: str | None = None) -> dict:
    """Run claude subprocess, return parsed result with exit_code."""
    claude_args = _build_claude_args(prompt, skill, session_id=session_id)
    result = subprocess.run(claude_args, capture_output=True, text=True)
    parsed = _parse_claude_output(result.stdout)
    parsed["exit_code"] = result.returncode
    if session_id and not parsed.get("session_id"):
        parsed["session_id"] = session_id
    return parsed


def _run_interactive_loop(initial_prompt: str, skill: str | None) -> dict:
    """Run claude interactively, looping through decision points.

    Returns merged result with combined text from all rounds.
    """
    parsed = _run_claude_with_session(initial_prompt, skill)
    session_id = parsed.get("session_id")
    all_text = parsed["text"]
    total_cost = parsed.get("cost_usd") or 0
    all_errors = list(parsed.get("errors") or [])
    latest_text = parsed["text"]

    for _ in range(1, MAX_INTERACTIVE_ROUNDS):
        decision = _extract_decision_from_output(latest_text)
        if not decision:
            break
        choice = _prompt_human_for_decision("interactive", decision)
        if not choice:
            print("[mgg] 决策跳过")
            break

        label = _find_choice_label(decision, choice)
        follow_prompt = f"用户选择了: {choice} — {label}\n继续执行。"
        print(f"[mgg] 继续执行 (选择: {label})")

        round_result = _run_claude_with_session(follow_prompt, skill=None,
                                                 session_id=session_id)
        if round_result["text"]:
            all_text += "\n" + round_result["text"]
        latest_text = round_result["text"]
        total_cost += round_result.get("cost_usd") or 0
        all_errors.extend(round_result.get("errors") or [])

    return {"text": all_text, "session_id": session_id,
            "cost_usd": total_cost, "errors": all_errors}


# ── decision channel ───────────────────────────────────────────────────


def _extract_decision_from_output(text: str) -> dict | None:
    """Extract structured decision data from claude output.

    Detects:
    1. JSON block in code fence: any ``` or ```json with 'options'/'choices' array
    2. Markdown decision table: ## section with table containing options

    Returns {"question": str, "options": [{"id", "label", "pros", "cons"}]} or None.
    """
    candidates = []

    # Pattern 1: JSON block in code fence — extract everything between backticks
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
    # Normalize: ensure each option has at least an id/label
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
    for match in re.finditer(r'(?:##|###|####)\s*(.*?)\n(.*?)(?=\n(?:##|###|####)|\Z)', text, re.DOTALL):
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


def _save_decision(task_dir: Path, decision: dict, choice: str):
    path = task_dir / "decision.json"
    data = {"decision": decision, "choice": choice,
            "choice_label": _find_choice_label(decision, choice),
            "decided_at": _now()}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"[mgg] 决策已保存 → {path}")


def _load_decision(task_dir: Path) -> dict | None:
    path = task_dir / "decision.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _find_choice_label(decision: dict, choice: str) -> str:
    for opt in decision.get("options", []):
        if opt.get("id") == choice:
            return opt.get("label", choice)
    return choice


def _inject_decision_into_prompt(prompt: str, decision_data: dict | None) -> str:
    if not decision_data:
        return prompt
    d = decision_data.get("decision", {})
    return (f"{prompt}\n\n"
            f"[决策注入] {d.get('question', '前序决策')} "
            f"→ 选择: {decision_data.get('choice_label', decision_data.get('choice', '?'))}")


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


def _wait_dependencies(dep_ids: list[str]):
    pending = set(dep_ids)
    while pending:
        for tid in list(pending):
            try:
                s = _load_task(tid)
                if s["status"] in ("done", "failed"):
                    pending.remove(tid)
            except SystemExit:
                pending.remove(tid)
        if pending:
            time.sleep(2)


def _print_status_line(state: dict):
    marks = {"done": "✓", "failed": "✗", "running": "…", "pending": "·", "blocked": "⊘"}
    m = marks.get(state["status"], "?")
    cost = f" ${state['cost_usd']:.3f}" if state.get("cost_usd") else ""
    err = f" — {state['error']}" if state.get("error") else ""
    print(f"[mgg] {m} {state['id']} [{state['status']}]{cost}{err}")


# ── status / ls / resume ─────────────────────────────────────────────

def cmd_status(args):
    if args.task_id:
        state = _load_task(args.task_id)
        print(json.dumps(state, indent=2, ensure_ascii=False))
        result_path = TASKS_DIR / args.task_id / "result.md"
        if result_path.exists():
            text = result_path.read_text().strip()
            if text:
                print(f"\n── result ────────────────────────────────")
                print(text[:1500])
        return

    if not TASKS_DIR.exists():
        print("[mgg] no tasks yet")
        return

    tasks = []
    for d in sorted(TASKS_DIR.iterdir()):
        if d.is_dir():
            try:
                tasks.append(_load_task(d.name))
            except Exception:
                pass

    if not tasks:
        print("[mgg] no tasks")
        return

    print(f"{'id':12} {'skill':10} {'status':8} {'cost':8}  prompt")
    print("-" * 60)
    for t in sorted(tasks, key=lambda x: x["created_at"], reverse=True):
        cost_str = f"${t['cost_usd']:.3f}" if t.get("cost_usd") else ""
        short = t["prompt"][:40]
        print(f"{t['id']:12} {t['skill']:10} {t['status']:8} {cost_str:8}  {short}")


def cmd_ls(args):
    skills = _discover_skills()
    if not skills:
        print("[mgg] no skills found")
        return
    print(f"{'name':18} description")
    print("-" * 60)
    for s in skills:
        desc = s.get("description", "")[:60]
        print(f"{s['name']:18} {desc}")


def cmd_resume(args):
    state = _load_task(args.task_id)
    print(f"[mgg] resuming {args.task_id} (previous: {state['status']})")

    class FakeArgs:
        prompt = state["prompt"]
        skill = state["skill"]
        dep = state.get("dependencies", [])
        inject = state.get("inject", None)

    return cmd_run(FakeArgs)


def cmd_decide(args):
    """Non-interactively record a decision for a task."""
    state = _load_task(args.task_id)
    task_dir = TASKS_DIR / args.task_id

    # Read result to extract decision
    result_path = task_dir / "result.md"
    if not result_path.exists():
        die(f"no result found for task {args.task_id}")
    text = result_path.read_text()
    decision = _extract_decision_from_output(text)
    if not decision:
        die(f"no structured decision found in task {args.task_id} output")

    choice = args.choice
    _save_decision(task_dir, decision, choice)
    state["decision"] = choice
    _save_task(state)
    print(f"[mgg] decision recorded: {choice}")
    _print_status_line(state)


# ── parser (module-level for testability) ──────────────────────────────

parser = argparse.ArgumentParser(
    prog="mgg",
    description="Project management CLI — spawns isolated Claude Code subprocesses per task.",
)
sub = parser.add_subparsers(dest="command", required=True)

p_run = sub.add_parser("run", help="Run a new task (spawn isolated claude subprocess)")
p_run.add_argument("prompt", help="Task description")
p_run.add_argument("--skill", "-s", help="Skill to route to (e.g. paa, pdu, ulw)")
p_run.add_argument("--no-skill", action="store_true", help="Skip skill routing, run prompt directly")
p_run.add_argument("--dep", nargs="*", default=[], help="Dependency task IDs (wait for completion first)")
p_run.add_argument("--inject", metavar="TASK_ID",
                   help="Inject decision from a previous task into this task's prompt")
p_run.add_argument("--interactive", "-i", action="store_true",
                   help="Enable interactive decision loop (pause for human input)")

p_st = sub.add_parser("status", help="Show task status")
p_st.add_argument("task_id", nargs="?", help="Task ID (omit to list all)")

sub.add_parser("ls", help="List available skills")

p_rs = sub.add_parser("resume", help="Resume a failed task")
p_rs.add_argument("task_id", help="Task ID to resume")

p_dc = sub.add_parser("decide", help="Record a decision for a completed task (non-interactive)")
p_dc.add_argument("task_id", help="Task ID containing the decision output")
p_dc.add_argument("choice", help="Selected option ID")


def main():
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "ls":
        cmd_ls(args)
    elif args.command == "resume":
        cmd_resume(args)
    elif args.command == "decide":
        cmd_decide(args)


if __name__ == "__main__":
    main()
