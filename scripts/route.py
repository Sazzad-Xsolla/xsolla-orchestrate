#!/usr/bin/env python3
"""Explain routing, or record a route before critique and dispatch."""
import argparse
import json
from pathlib import Path
from control import load_run, locked_json, now, orchestrator_only, read_json, task_by_id

CONFIG = Path(__file__).resolve().parent.parent / "config" / "routing.json"


def recommend(task, config=None):
    shape = task.get("shape", "spec")
    routes = (config or read_json(CONFIG))["routes"]
    if shape not in routes:
        raise ValueError("Unknown task shape: " + str(shape))
    risk = task.get("risk", "normal")
    if risk not in ("normal", "high"):
        raise ValueError("risk must be normal or high")
    selected = "tricky" if risk == "high" and shape in ("lookup", "mechanical", "spec") else shape
    result = dict(routes[selected])
    result.update(shape=selected, runtime="headless", policy_version=(config or read_json(CONFIG))["version"])
    if selected != shape:
        result["reason"] += "; raised from " + shape + " because risk is high"
    return result


def apply_route(run, task_id):
    orchestrator_only()
    run, _, _ = load_run(run)
    with locked_json(run / "plan.json") as plan:
        task = task_by_id(plan, task_id)
        if task.get("state", "planned") not in ("planned", "failed", "blocked"):
            raise ValueError("Routing can only change before dispatch or after review")
        if task.get("routing_history"):
            raise ValueError("An escalated task keeps its recorded route; use escalate.py")
        route = recommend(task)
        task.update({k: route[k] for k in ("shape", "model", "effort", "runtime", "budget_usd")})
        task["routing_reason"] = route["reason"]
        task["routing_policy_version"] = route["policy_version"]
        plan.setdefault("log", []).append({"at": now(), "note": task_id + ": " + route["reason"]})
    return route


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run")
    ap.add_argument("task")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    _, plan, _ = load_run(args.run)
    result = apply_route(args.run, args.task) if args.apply else recommend(task_by_id(plan, args.task))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError) as error:
        raise SystemExit(str(error))
