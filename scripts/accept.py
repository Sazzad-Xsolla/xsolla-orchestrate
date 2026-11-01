#!/usr/bin/env python3
"""Run a task's boss-only acceptance check and record the result in plan.json.

Usage: accept.py <run_dir> <task_id> [--dry]
  --dry  run the check without recording (use before dispatch to prove it executes)

The check is the task's `accept` command, run from the project root with a 10-minute
timeout. Exit code is the check's own (0 = pass).
"""
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    from control import load_run, locked_json, orchestrator_only, task_by_id
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    orchestrator_only()
    run, plan, _ = load_run(sys.argv[1])
    task_id = sys.argv[2]
    dry = "--dry" in sys.argv
    task = task_by_id(plan, task_id)
    cmd = task.get("accept")
    attempt = task.get("attempt", 1)
    if not cmd:
        sys.exit("Write a meaningful acceptance command before dispatch")
    start = time.time()
    try:
        result = subprocess.run(cmd, shell=True, cwd=plan["project_dir"],
                                capture_output=True, text=True, timeout=600)
        code, out = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        code, out = 124, "timed out after 600s"
    tail = "\n".join(out.strip().splitlines()[-15:])
    print(tail)
    print(f"accept {task_id}: {'PASS' if code == 0 else 'FAIL'} (exit {code}, {time.time() - start:.1f}s)")
    if not dry:
        with locked_json(run / "plan.json") as latest:
            current = task_by_id(latest, task_id)
            if current.get("accept") != cmd or current.get("attempt", 1) != attempt:
                sys.exit("Task changed while acceptance ran; rerun against the current task")
            current.setdefault("accept_results", []).append({
                "at": time.strftime("%H:%M:%S"), "attempt": attempt,
                "passed": code == 0, "exit": code, "tail": tail[-1500:]})
    sys.exit(code)


if __name__ == "__main__":
    main()
