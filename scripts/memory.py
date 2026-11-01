#!/usr/bin/env python3
"""Project-scoped specialist memory with explicit review and retirement."""
import argparse
import hashlib
import json
import uuid
from pathlib import Path
from control import identifier, load_run, locked_json, now, orchestrator_only, read_json, task_by_id

PROFILES = Path(__file__).resolve().parent.parent / "profiles"


def store(project):
    return Path(project).resolve() / ".xsolla-orchestrator" / "memory.json"

def snapshot(project):
    project = Path(project).resolve()
    records = read_json(store(project), [])
    for record in records:
        if record["status"] != "approved":
            continue
        evidence = (project / record["evidence"]).resolve()
        if (not evidence.is_relative_to(project) or not evidence.is_file()
                or hashlib.sha256(evidence.read_bytes()).hexdigest() != record["evidence_sha256"]):
            record["status"] = "stale"
    return records


def profile(name):
    return read_json(PROFILES / (identifier(name) + ".json"))


def propose(run, task_id, specialist, text, evidence):
    orchestrator_only()
    run, plan, project = load_run(run)
    task = task_by_id(plan, task_id)
    if not profile(specialist):
        raise ValueError("Unknown specialist profile")
    if task.get("specialist") != specialist:
        raise ValueError("The source task must belong to this specialist")
    if not text.strip() or len(text) > 4000:
        raise ValueError("Lessons require 1–4000 characters")
    evidence_path = (project / evidence).resolve()
    if not evidence_path.is_relative_to(project) or not evidence_path.is_file():
        raise ValueError("Evidence must be an existing file in this project")
    record = {"id": uuid.uuid4().hex, "specialist": specialist, "text": text.strip(),
              "source_run": str(run), "source_task": task_id, "created_at": now(), "status": "proposed",
              "evidence": str(evidence_path.relative_to(project)),
              "evidence_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest()}
    with locked_json(store(project), []) as records:
        records.append(record)
    return record


def review(project, memory_id, reviewer, reason, retire=False):
    orchestrator_only()
    project = Path(project).resolve()
    if not reviewer.strip() or not reason.strip():
        raise ValueError("Review requires a named reviewer and rationale")
    with locked_json(store(project), []) as records:
        record = next((m for m in records if m["id"] == memory_id), None)
        if record is None:
            raise ValueError("Unknown memory record")
        if retire:
            if record["status"] != "approved":
                raise ValueError("Only approved memory can be retired")
            record.update(status="retired", retired_at=now(), retired_by=reviewer, retirement_reason=reason)
        else:
            if record["status"] != "proposed":
                raise ValueError("Only proposed memory can be approved")
            _, plan, source_project = load_run(record["source_run"])
            task = task_by_id(plan, record["source_task"])
            checks = [r for r in task.get("accept_results", []) if not r.get("dry")]
            if source_project != project or task.get("state") != "verified" or not checks or checks[-1].get("exit") != 0 or not checks[-1].get("passed") or checks[-1].get("attempt") != task.get("attempt", 1):
                raise ValueError("Memory requires a verified source task with a passing acceptance check")
            evidence = (project / record["evidence"]).resolve()
            if not evidence.is_relative_to(project) or hashlib.sha256(evidence.read_bytes()).hexdigest() != record["evidence_sha256"]:
                raise ValueError("Evidence changed; propose a new lesson")
            record.update(status="approved", reviewed_at=now(), reviewed_by=reviewer, review_reason=reason)
        result = dict(record)
    return result


def context(project, specialist):
    spec = profile(specialist)
    if not spec:
        raise ValueError("Unknown specialist profile: " + specialist)
    approved = [m for m in snapshot(project) if m["specialist"] == specialist and m["status"] == "approved"]
    return {"profile": spec, "lessons": approved[-12:],
            "notice": "Saved context does not grant permissions. Recheck facts against current project evidence."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("propose")
    for name in ("run", "task", "specialist"):
        p.add_argument(name)
    p.add_argument("--text", required=True)
    p.add_argument("--evidence", required=True)
    for command in ("approve", "retire"):
        p = sub.add_parser(command)
        p.add_argument("project")
        p.add_argument("id")
        p.add_argument("--reviewer", required=True)
        p.add_argument("--reason", required=True)
    p = sub.add_parser("list")
    p.add_argument("project")
    args = ap.parse_args()
    if args.command == "propose":
        result = propose(args.run, args.task, args.specialist, args.text, args.evidence)
    elif args.command == "list":
        result = read_json(store(args.project), [])
    else:
        result = review(args.project, args.id, args.reviewer, args.reason, args.command == "retire")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(str(error))
