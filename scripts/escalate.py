#!/usr/bin/env python3
"""Apply the escalation ladder to a task after a failed check, based on WHY it failed.

Usage: escalate.py <run_dir> <task_id> --cause brief|capability|budget|environment|resume
                   [--gap "what was wrong and what fixed looks like"] [--budget USD] [--keep]

  brief        the brief was missing or wrong about something. Same model and effort;
               the correction goes into the brief and the worker resumes its session.
  capability   the brief was clear and the worker still got it wrong. Raise effort one
               notch (model once effort is already high); fresh session; files rolled back.
  budget       the worker reached its cost checkpoint. The checkpoint is not a limit: if
               the watchdog finds it healthy, the checkpoint doubles (or --budget) and it
               resumes its session. If not, exits 6: treat it as paused and ask the user.
  environment  something outside the worker broke (missing tool, flaky service). Fix the
               environment first; the worker resumes.
  resume       the user chose to let a paused worker continue; --gap carries their guidance.

budget, environment and resume never count toward the 3 attempts. --gap is required for
brief, capability and resume. --keep skips rolling back files on a capability step.
Exits 4 without changing anything when the task has used its 3 counted attempts, or is
already at the top tier: stop and ask the user.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

EFFORTS = ["low", "medium", "high"]
MODELS = ["sonnet", "opus"]
MAX_COUNTED = 3
SKILL = Path(__file__).resolve().parent.parent


def last_session(wdir):
    for name in ("meta.json",):
        p = wdir / name
        if p.exists():
            return json.loads(p.read_text()).get("session_id") or None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("task_id")
    ap.add_argument("--cause", required=True, choices=["brief", "capability", "budget", "environment", "resume"])
    ap.add_argument("--gap")
    ap.add_argument("--budget", type=float)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    run = Path(a.run_dir).resolve()
    plan_path = run / "plan.json"
    plan = json.loads(plan_path.read_text())
    task = next((t for t in plan["tasks"] if t["id"] == a.task_id), None)
    if task is None:
        sys.exit(f"task {a.task_id} not in plan.json")
    wdir = run / "workers" / a.task_id
    if not a.gap:
        if a.cause in ("brief", "capability", "resume"):
            sys.exit(f"--gap is required for --cause {a.cause}")
        a.gap = ("You reached your cost checkpoint while still making progress. Continue exactly where you left off."
                 if a.cause == "budget" else "The environment problem is fixed. Continue where you left off.")

    if a.cause == "budget":
        # Spend alone never stops a worker; behaviour does.
        check = subprocess.run([sys.executable, str(SKILL / "scripts" / "watchdog.py"), str(run), a.task_id],
                               capture_output=True, text=True)
        if check.returncode != 0:
            signals = json.loads(check.stdout).get("signals", [])
            print("UNHEALTHY: not extending. Treat as paused and ask the user. Signals: "
                  + "; ".join(s["detail"] for s in signals))
            sys.exit(6)

    uncounted = ("environment", "budget", "resume")
    counted = sum(1 for h in task.get("routing_history", []) if h.get("cause") not in uncounted) + 1
    if a.cause not in uncounted and counted >= MAX_COUNTED:
        print(f"STOP: {a.task_id} has failed {counted} counted attempts. Report to the user and ask how to proceed.")
        sys.exit(4)

    before = f"{task['model']}/{task['effort']} ${task.get('budget_usd')}"
    resume = last_session(wdir)
    rollback = False
    if a.cause == "capability":
        if task["effort"] in EFFORTS[:-1]:
            task["effort"] = EFFORTS[EFFORTS.index(task["effort"]) + 1]
        elif task["model"] in MODELS[:-1]:
            task["model"] = MODELS[MODELS.index(task["model"]) + 1]
        else:
            print(f"STOP: {a.task_id} is already at the top tier. Ask the user.")
            sys.exit(4)
        resume = None  # a different tier can't reuse the session's cache
        rollback = not a.keep
    elif a.cause == "budget":
        task["budget_usd"] = a.budget or round(2 * float(task.get("budget_usd") or 1), 2)
    if a.budget is not None:
        task["budget_usd"] = a.budget

    task["attempt"] = task.get("attempt", 1) + 1
    task["state"] = "planned"
    task["resume_session"] = resume
    after = f"{task['model']}/{task['effort']} ${task.get('budget_usd')}"

    now = time.strftime("%H:%M")
    task.setdefault("routing_history", []).append({
        "at": now, "attempt": task["attempt"], "cause": a.cause, "from": before, "to": after,
        "resumed": bool(resume), "rolled_back": rollback, "gap": a.gap})
    gap_line = a.gap.strip().splitlines()[0][:120]
    plan.setdefault("log", []).append({"at": now, "note":
        f"{a.task_id} attempt {task['attempt']} ({a.cause}): {before} -> {after}"
        f"{', resumes session' if resume else ', fresh session'}{', files rolled back' if rollback else ''}. "
        f"Gap: {gap_line}"})
    from control import locked_json, task_by_id
    with locked_json(plan_path) as latest:
        current = task_by_id(latest, a.task_id)
        if current.get("attempt", 1) != task["attempt"] - 1:
            sys.exit("Task changed during recovery; inspect the current attempt")
        current.update(task)
        latest.setdefault("log", []).append(plan["log"][-1])

    if rollback:
        subprocess.run([sys.executable, str(SKILL / "scripts" / "snapshot.py"), str(run), a.task_id, "restore"], check=True)

    with (wdir / "brief.md").open("a") as f:
        f.write(f"\n\n## Correction (attempt {task['attempt']})\n"
                f"Your previous attempt did not pass the orchestrator's check (cause: {a.cause}).\n\n{a.gap}\n")
    print(f"{a.task_id}: attempt {task['attempt']} ready at {after} "
          f"({'resume' if resume else 'fresh'}); dispatch with spawn_worker.sh")


if __name__ == "__main__":
    main()
