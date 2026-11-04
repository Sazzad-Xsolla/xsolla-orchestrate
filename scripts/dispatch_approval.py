#!/usr/bin/env python3
"""Record explicit chat confirmation and block agent launches for unconfirmed plans."""
import argparse
import hashlib
import json
from pathlib import Path

from control import load_run, locked_json, now, orchestrator_only


def fingerprint(run, plan):
    # Execution state, evidence and display metadata change during normal work.
    # Scope, spending, access and acceptance changes require a fresh confirmation.
    fields = ("id", "title", "objective", "shape", "runtime", "model", "effort",
              "budget_usd", "writes", "add_dirs", "skills", "specialist",
              "depends_on", "done_criteria", "accept")
    done = [item.get("text") if isinstance(item, dict) else item
            for item in plan.get("definition_of_done", [])]
    reviewed = {
        "run": str(Path(run).resolve()),
        "project": str(Path(plan["project_dir"]).resolve()),
        "goal": plan.get("goal"), "definition_of_done": done,
        "verification_plan": plan.get("verification_plan"),
        "run_budget_usd": plan.get("run_budget_usd"),
        "tasks": [{key: task.get(key) for key in fields} for task in plan["tasks"]],
    }
    return hashlib.sha256(json.dumps(reviewed, sort_keys=True).encode()).hexdigest()


def require_approval(run, plan):
    record = plan.get("dispatch_confirmation") or {}
    if (not record.get("confirmation") or record.get("source") != "chat"
            or record.get("fingerprint") != fingerprint(run, plan)):
        raise ValueError("Dispatch plan is unconfirmed or changed; show the plan and wait for explicit user confirmation before any critic or worker starts")


def approve(run, confirmation):
    orchestrator_only()
    if not confirmation.strip():
        raise ValueError("Record the user's actual explicit confirmation")
    run, _, _ = load_run(run)
    with locked_json(run / "plan.json") as plan:
        if not plan.get("goal") or not plan["tasks"]:
            raise ValueError("Prepare the goal and dispatch table before recording confirmation")
        plan["dispatch_confirmation"] = {
            "source": "chat", "confirmation": confirmation.strip(),
            "at": now(), "fingerprint": fingerprint(run, plan),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("action", choices=("check", "approve"))
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args()
    if args.action == "approve":
        approve(args.run, args.confirmation)
    else:
        run, plan, _ = load_run(args.run)
        require_approval(run, plan)
    print("Dispatch confirmation recorded" if args.action == "approve" else "Dispatch plan confirmed")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
