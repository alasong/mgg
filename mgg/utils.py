"""General utility functions for mgg."""

import sys
import time
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def die(msg: str, code: int = 1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def _wait_dependencies(dep_ids: list[str]):
    from mgg.persistence import _load_task  # lazy import to avoid circular dependency

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
