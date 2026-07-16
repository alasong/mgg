"""Claude Code subprocess management and interactive loop for mgg."""

import json
import subprocess
import uuid

import sys

from mgg.decision import _extract_decision_from_output, _prompt_human_for_decision
from mgg.persistence import _find_choice_label, _save_task
from mgg.constants import TASKS_DIR, SKILLS_DIR
from mgg.utils import _now

MAX_INTERACTIVE_ROUNDS = 5


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
    max_rounds = MAX_INTERACTIVE_ROUNDS
    if skill:
        from mgg.router import _parse_skill_meta
        skill_md = SKILLS_DIR / skill / "SKILL.md"
        if skill_md.exists():
            meta = _parse_skill_meta(skill_md)
            max_rounds = int(meta.get("max_interactive_rounds", max_rounds))

    parsed = _run_claude_with_session(initial_prompt, skill)
    session_id = parsed.get("session_id")
    all_text = parsed["text"]
    total_cost = parsed.get("cost_usd") or 0
    all_errors = list(parsed.get("errors") or [])
    latest_text = parsed["text"]

    for _ in range(1, max_rounds):
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


def _run_single_task(state: dict, skill: str | None) -> tuple[dict, dict]:
    """Execute a single batch task, update state in place, return (state, parsed)."""
    prompt = state["prompt"]
    claude_args = _build_claude_args(prompt, skill)
    result = subprocess.run(claude_args, capture_output=True, text=True)
    parsed = _parse_claude_output(result.stdout)

    state["exit_code"] = result.returncode
    state["cost_usd"] = parsed.get("cost_usd")
    state["session_id"] = parsed.get("session_id")

    result_text = parsed.get("text", "").strip()
    if result_text:
        result_path = TASKS_DIR / state["id"] / "result.md"
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
    return state, parsed


def _run_tasks_parallel(prompts: list[str], skill: str | None, max_workers: int = 3) -> list[dict]:
    """Run multiple prompts in parallel using ThreadPoolExecutor."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    states = []
    for prompt in prompts:
        task_id = uuid.uuid4().hex[:12]
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
            "dependencies": [],
            "inject": None,
        }
        _save_task(state)
        states.append(state)
        print(f"[mgg] task {task_id} — skill={skill} (parallel)")
        sys.stdout.flush()

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_run_single_task, s, skill): s for s in states}
        for future in as_completed(future_map):
            state = future_map[future]
            try:
                state, _ = future.result()
            except Exception as e:
                state["status"] = "failed"
                state["error"] = str(e)
                _save_task(state)
            results.append(state)

    return results
