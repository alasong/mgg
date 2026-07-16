"""Task and decision persistence layer for mgg."""

import json
from pathlib import Path

from mgg.constants import TASKS_DIR
from mgg.utils import _now, die


def _load_task(task_id: str) -> dict:
    path = TASKS_DIR / task_id / "state.json"
    if not path.exists():
        die(f"task not found: {task_id}")
    return json.loads(path.read_text())


def _save_task(state: dict):
    task_dir = TASKS_DIR / state["id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _save_decision(task_dir: Path, decision: dict, choice: str):
    path = task_dir / "decision.json"
    data = {
        "decision": decision,
        "choice": choice,
        "choice_label": _find_choice_label(decision, choice),
        "decided_at": _now(),
    }
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
