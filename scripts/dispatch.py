#!/usr/bin/env python3
"""Validate and reserve a task, assemble context, then launch the existing worker runtime."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import coordinate
import memory
from control import atomic_json, load_run, locked_json, now, orchestrator_only, read_json, task_by_id

SKILL = Path(__file__).resolve().parent.parent
ACTIVE = ("running", "dispatching")


def critique_fingerprint(run, task):
    brief = run / "workers" / task["id"] / "brief.md"
    reviewed = {key: task.get(key) for key in ("id", "title", "objective", "writes", "depends_on", "done_criteria", "accept", "model", "effort", "specialist")}
    return hashlib.sha256(brief.read_bytes() + json.dumps(reviewed, sort_keys=True).encode()).hexdigest()


def write_paths(task, project):
    project = Path(project).resolve()
    paths = []
    for value in task.get("writes", []):
        if any(c in value for c in "*?["):
            raise ValueError("Write lists use literal files or directories, not globs")
        path = (project / value).resolve()
        controls = project / ".xsolla-orchestrator"
        if not path.is_relative_to(project) or path == project or path == controls or path.is_relative_to(controls) or path.is_relative_to(project / ".git"):
            raise ValueError("Write lists must stay inside project source and exclude orchestration records")
        paths.append(path)
    return paths


def validate(run, plan, project, task_id):
    task = task_by_id(plan, task_id)
    if task.get("state", "planned") not in ("planned", "failed", "blocked"):
        raise ValueError("Task is not ready for dispatch; review or recover it first")
    for dependency in task.get("depends_on", []):
        if task_by_id(plan, dependency).get("state") != "verified":
            raise ValueError("Dependency is not verified: " + dependency)
    if task.get("model") not in ("sonnet", "opus") or task.get("effort") not in ("low", "medium", "high"):
        raise ValueError("Select a supported route before dispatch")
    if not task.get("routing_reason"):
        raise ValueError("Record a routing reason before dispatch")
    if float(task.get("budget_usd", 0)) <= 0:
        raise ValueError("Task checkpoint must be positive")
    brief_path = run / "workers" / task_id / "brief.md"
    brief = brief_path.read_text() if brief_path.exists() else ""
    if not brief.strip() or re.search(r"\{\{.+?\}\}|<note>|<source files>|<test files>|<command[^>]*>|TODO", brief + task.get("accept", "") + json.dumps(task.get("writes", []))):
        raise ValueError("Complete the task brief and acceptance command before dispatch")
    if not task.get("accept") or not task.get("done_criteria"):
        raise ValueError("Define acceptance criteria and a runnable check")
    audit = read_json(brief_path.parent / "critique-audit.json", {})
    if audit.get("verdict") != "clear" or audit.get("fingerprint") != critique_fingerprint(run, task):
        raise ValueError("Run critique_brief.sh against the current brief and task configuration")
    if task.get("specialist"):
        memory.context(project, task["specialist"])
    active = [t for t in plan["tasks"] if t.get("state") in ACTIVE]
    if len(active) >= 4:
        raise ValueError("Four workers are already reserved or running")
    writes = write_paths(task, project)
    for worker in active:
        for left in writes:
            for right in write_paths(worker, project):
                if left == right or left.is_relative_to(right) or right.is_relative_to(left):
                    raise ValueError("Write ownership overlaps active task " + worker["id"])
    return task


def claim(run, task_id):
    orchestrator_only()
    run, _, project = load_run(run)
    with locked_json(run / "plan.json") as plan:
        task = validate(run, plan, project, task_id)
        task.update(state="dispatching", dispatch_owner_pid=os.getpid(), dispatch_started_at=now())
    return task, project


def dispatch(run, task_id):
    run = Path(run).resolve()
    task, project = claim(run, task_id)
    code = 2
    try:
        peer = coordinate.context(run, task_id, mark=True)
        specialist = memory.context(project, task["specialist"]) if task.get("specialist") else None
        context = {"peer_context": peer, "specialist_context": specialist}
        atomic_json(run / "workers" / task_id / "dispatch-context.json", context)
        with locked_json(run / "plan.json") as plan:
            task_by_id(plan, task_id)["state"] = "running"
        env = dict(os.environ, XSOLLA_DISPATCH_TASK=task_id)
        code = subprocess.run(["bash", str(SKILL / "scripts" / "spawn_worker.sh"), str(run), task_id], env=env).returncode
        return code
    finally:
        with locked_json(run / "plan.json") as plan:
            task = task_by_id(plan, task_id)
            if task.get("state") in ACTIVE:
                meta = read_json(run / "workers" / task_id / "meta.json", {})
                task["state"] = "awaiting review" if meta.get("ended_at") else "failed"
            task["dispatch_exit_code"] = code
            task["dispatch_finished_at"] = now()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run")
    ap.add_argument("task")
    ap.add_argument("--check", action="store_true", help="Validate without launching a worker")
    ap.add_argument("--fingerprint", action="store_true", help="Print current critic input fingerprint")
    args = ap.parse_args()
    run, plan, project = load_run(args.run)
    if args.fingerprint:
        print(critique_fingerprint(run, task_by_id(plan, args.task)))
    elif args.check:
        validate(run, plan, project, args.task)
        print("Ready for dispatch")
    else:
        raise SystemExit(dispatch(run, args.task))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(str(error))
