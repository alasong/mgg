"""CLI command layer for mgg."""

import argparse
import json
import subprocess
import sys
import uuid

from mgg.analyzer import _preflight_analyze, _batch_prompt_human, _build_injection_text
from mgg.decision import _extract_decision_from_output, _inject_decision_into_prompt, _prompt_human_for_decision
from mgg.executor import _run_interactive_loop, _run_single_task, _run_tasks_parallel
from mgg.persistence import _load_task, _save_task, _save_decision, _load_decision
from mgg.router import _infer_skill, _discover_skills, _parse_skill_meta
from mgg.constants import TASKS_DIR, SKILLS_DIR
from mgg.utils import _now, die, _wait_dependencies, _print_status_line


def cmd_run(args):
    prompts = args.prompt  # list (nargs='+')
    skill = args.skill if args.skill else None
    interactive = getattr(args, "interactive", False)
    parallel_mode = getattr(args, "parallel", False)

    if args.dep:
        _wait_dependencies(args.dep)

    if parallel_mode:
        if not skill:
            skill = _infer_skill(prompts[0])
        max_workers = getattr(args, "max_workers", 3)
        if max_workers == 3 and skill:
            skill_md = SKILLS_DIR / skill / "SKILL.md"
            if skill_md.exists():
                meta = _parse_skill_meta(skill_md)
                max_workers = int(meta.get("max_workers", 3))
        results = _run_tasks_parallel(prompts, skill, max_workers)
        for state in results:
            _print_status_line(state)
        return results[-1] if results else None

    # Single task mode
    prompt = prompts[0]
    if not skill and not getattr(args, "no_skill", False):
        skill = _infer_skill(prompt)
    inject_id = getattr(args, "inject", None)
    task_id = uuid.uuid4().hex[:12]

    decision_data = None
    if inject_id:
        dep_dir = TASKS_DIR / inject_id
        decision_data = _load_decision(dep_dir)
        if decision_data:
            prompt = _inject_decision_into_prompt(prompt, decision_data)
            print(f"[mgg] injected decision from task {inject_id}")
        else:
            print(f"[mgg] warning: no decision found in task {inject_id}")

    # Preflight analysis (default on, --no-preflight to skip)
    no_preflight = getattr(args, "no_preflight", False)
    if not no_preflight and not interactive:
        decisions = _preflight_analyze(prompt, skill_name=skill)
        if decisions:
            choices = _batch_prompt_human(decisions)
            if choices:
                inject_text = _build_injection_text(decisions, choices)
                prompt = prompt + inject_text
                print(f"[mgg] 预分析: {len(choices)}/{len(decisions)} 个决策已确认")

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

    print(f"[mgg] task {task_id} — skill={skill} ({'interactive' if interactive else 'batch'})")
    sys.stdout.flush()

    if interactive:
        parsed = _run_interactive_loop(prompt, skill)
        state["cost_usd"] = parsed.get("cost_usd")
        state["session_id"] = parsed.get("session_id")
        state["exit_code"] = 0
        if parsed.get("errors"):
            state["exit_code"] = 1
        result_text = parsed.get("text", "").strip()
        if result_text:
            result_path = TASKS_DIR / task_id / "result.md"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(result_text)
        state["status"] = "done" if state["exit_code"] == 0 else "failed"
        state["finished_at"] = _now()
        _save_task(state)
    else:
        state, parsed = _run_single_task(state, skill)

    if not interactive and state["status"] == "done":
        result_text = parsed.get("text", "").strip()
        decision = _extract_decision_from_output(result_text)
        if decision:
            choice = _prompt_human_for_decision(task_id, decision)
            if choice:
                _save_decision(TASKS_DIR / task_id, decision, choice)
                state["decision"] = choice
                _save_task(state)

    if parsed.get("text", "").strip():
        print(f"\n── result ──────────────────────────────────")
        result_text = parsed.get("text", "").strip()
        print(result_text[:2000])
        if len(result_text) > 2000:
            result_path = TASKS_DIR / task_id / "result.md"
            print(f"\n... (truncated, full at {result_path})")
        print()

    _print_status_line(state)
    return state


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
        prompt = [state["prompt"]]
        skill = state["skill"]
        dep = state.get("dependencies", [])
        inject = state.get("inject", None)
        interactive = False
        parallel = False

    return cmd_run(FakeArgs)


def cmd_decide(args):
    state = _load_task(args.task_id)
    task_dir = TASKS_DIR / args.task_id

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


# ── parser ──────────────────────────────────────────────────────

parser = argparse.ArgumentParser(
    prog="mgg",
    description="Project management CLI — spawns isolated Claude Code subprocesses per task.",
)
sub = parser.add_subparsers(dest="command", required=True)

p_run = sub.add_parser("run", help="Run a new task (spawn isolated claude subprocess)")
p_run.add_argument("prompt", nargs="+", help="Task description (or multiple prompts with --parallel)")
p_run.add_argument("--skill", "-s", help="Skill to route to (e.g. paa, pdu, ulw)")
p_run.add_argument("--no-skill", action="store_true", help="Skip skill routing, run prompt directly")
p_run.add_argument("--dep", nargs="*", default=[], help="Dependency task IDs (wait for completion first)")
p_run.add_argument("--inject", metavar="TASK_ID",
                   help="Inject decision from a previous task into this task's prompt")
p_run.add_argument("--interactive", "-i", action="store_true",
                   help="Enable interactive decision loop (pause for human input)")
p_run.add_argument("--parallel", action="store_true",
                   help="Run multiple prompts in parallel")
p_run.add_argument("--max-workers", type=int, default=3,
                   help="Max parallel workers (default: 3)")
p_run.add_argument("--no-preflight", action="store_true",
                   help="Skip preflight analysis of decision points")

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
