#!/usr/bin/env python3
"""Launch an explicit group of independent workers before waiting for any of them."""
import argparse
import copy
from pathlib import Path
import subprocess
import sys

from control import load_run, locked_json, orchestrator_only, task_by_id
from dispatch import validate


def check_wave(run, task_ids):
    orchestrator_only()
    if not task_ids or len(set(task_ids)) != len(task_ids):
        raise ValueError("Provide a nonempty group of unique task IDs")
    run, _, project = load_run(run)
    with locked_json(run / "plan.json") as current:
        plan = copy.deepcopy(current)
        for task_id in task_ids:
            validate(run, plan, project, task_id)
            # Simulate reservations so capacity and write conflicts within this
            # group are checked too, without mutating the actual plan.
            task_by_id(plan, task_id)["state"] = "dispatching"
    return run


def dispatch_wave(run, task_ids):
    run = check_wave(run, task_ids)
    children = []
    results = {}
    try:
        for task_id in task_ids:
            log = run / "workers" / task_id / "dispatch.log"
            with log.open("a") as output:
                process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).with_name("dispatch.py")), str(run), task_id],
                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                )
            children.append((task_id, process))
            print(f"Launched dispatcher for {task_id}: pid={process.pid}, log={log}", flush=True)
    finally:
        # All launches happen above. Waiting here cannot serialize the group.
        # Reap started children even if a later process fails to launch.
        for task_id, process in children:
            results[task_id] = process.wait()
            print(f"Dispatcher {task_id} exited {results[task_id]}", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("tasks", nargs="+")
    parser.add_argument("--check", action="store_true", help="Preflight the entire group without launching workers")
    args = parser.parse_args()
    if args.check:
        check_wave(args.run, args.tasks)
        print("Independent group ready for parallel dispatch")
        return 0
    results = dispatch_wave(args.run, args.tasks)
    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(str(error))
