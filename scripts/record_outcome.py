#!/usr/bin/env python3
"""Append a finished task's outcome to the skill's routing history.

Usage: record_outcome.py <run_dir> <task_id> verified|abandoned
Call it once per task when it is verified or given up on.
"""
import json
import sys
import time
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
HISTORY = SKILL / "history.jsonl"


def main():
    if len(sys.argv) < 4 or sys.argv[3] not in ("verified", "abandoned"):
        sys.exit(__doc__)
    run, task_id, outcome = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
    sys.path.insert(0, str(SKILL / "scripts"))
    import status  # reuse its cost accounting

    plan = json.loads((run / "plan.json").read_text())
    task = next(t for t in plan["tasks"] if t["id"] == task_id)
    history = task.get("routing_history", [])
    first = history[0]["from"] if history else f"{task['model']}/{task['effort']}"
    counted = [h for h in history if h.get("cause") != "environment"]
    row = {
        "date": time.strftime("%Y-%m-%d"), "run": plan.get("run_id"), "task": task_id,
        "shape": task.get("shape", "unknown"), "runtime": task.get("runtime", "headless"),
        "first_tier": first.split(" ")[0], "final_tier": f"{task['model']}/{task['effort']}",
        "attempts": task.get("attempt", 1), "first_pass": outcome == "verified" and not counted,
        "causes": [h.get("cause") for h in history], "outcome": outcome,
        "cost_usd": round(status.task_cost(run / "workers" / task_id), 4),
        "critic_flagged": (run / "workers" / task_id / "critique.md").exists()
                          and "needs-fixes" in (run / "workers" / task_id / "critique.md").read_text(),
    }
    with HISTORY.open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"recorded {task_id}: {outcome}, first_pass={row['first_pass']}, ${row['cost_usd']}")


if __name__ == "__main__":
    main()
