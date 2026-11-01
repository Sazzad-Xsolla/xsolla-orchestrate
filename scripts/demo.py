#!/usr/bin/env python3
"""Create synthetic run evidence and exercise handoffs and memory without model calls."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import coordinate
import dispatch
import memory
import route
from control import atomic_json, now


def create(output):
    project = Path(output).resolve()
    project.mkdir(parents=True, exist_ok=False)
    run = project / ".xsolla-orchestrator/demo"
    run.mkdir(parents=True)
    (project / "events.md").write_text("Exported event timestamps must include an explicit UTC offset.\n")
    tasks = []
    examples = [("impl", "Implement event export", "spec", "implementation", "verified"),
                ("review", "Review timestamp handling", "review", "review", "planned"),
                ("triage", "Investigate retry behavior", "lookup", None, "paused")]
    for task_id, title, shape, specialist, state in examples:
        task = {"id": task_id, "title": title, "shape": shape, "state": state, "specialist": specialist,
                "writes": [], "depends_on": ["impl"] if task_id == "review" else [], "attempt": 1,
                "done_criteria": ["Timestamp contract is documented"],
                "accept": "python3 -c 'from pathlib import Path; assert \"UTC offset\" in Path(\"events.md\").read_text()'"}
        selection = route.recommend(task)
        task.update({k: selection[k] for k in ("model", "effort", "runtime", "budget_usd")})
        task["routing_reason"] = selection["reason"]
        if state == "verified":
            task["accept_results"] = [{"attempt": 1, "passed": True, "exit": 0, "at": now(), "tail": "Synthetic demonstration evidence"}]
        tasks.append(task)
        worker = run / "workers" / task_id
        worker.mkdir(parents=True)
        (worker / "brief.md").write_text("# " + title + "\n\nCheck the event timestamp contract in events.md and report evidence.\n")
        (worker / "critique.md").write_text("VERDICT: clear\n")
        atomic_json(worker / "critique-audit.json", {"verdict": "clear", "fingerprint": dispatch.critique_fingerprint(run, task)})
        if state == "planned":
            continue
        atomic_json(worker / "meta.json", {"runtime": "headless", "ended_at": 1760000010, "started_at": 1760000000})
        event = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Checked the timestamp contract and recorded the handoff"}]}}
        (worker / "log.jsonl").write_text(json.dumps(event) + "\n" + json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 0}) + "\n")
    plan = {"run_id": "demo", "title": "Event export review", "project_dir": str(project), "demo": True,
            "goal": "Coordinate implementation and review, share the timestamp contract, and retain a reviewed project lesson.",
            "dashboard_theme": "xsolla", "tasks": tasks, "approvals": [], "run_budget_usd": 10,
            "definition_of_done": [{"text": "The timestamp contract is verified", "met": True, "evidence": "events.md"},
                                   {"text": "Independent review is complete", "met": False}],
            "log": [{"at": "10:02", "note": "Critic cleared the implementation and review briefs"},
                    {"at": "10:04", "note": "Implementation passed its acceptance check"},
                    {"at": "10:05", "note": "Watchdog paused triage after repeated calls; awaiting direction"}]}
    atomic_json(run / "plan.json", plan)
    atomic_json(run / "workers/triage/watchdog.json", {"signals": [{"signal": "repeat_call", "detail": "The same inspection call repeated without a changed result"}]})
    coordinate.send(run, "impl", "review", "handoff", "Export timestamps include a UTC offset. Verify the boundary cases against this contract.", "events.md:1")
    lesson = memory.propose(run, "impl", "implementation", "Exported event timestamps include an explicit UTC offset", "events.md")
    memory.review(project, lesson["id"], "Demo reviewer", "Synthetic example of reviewing verified project evidence")
    # A second run proves context is project-scoped rather than tied to one worker session.
    followup = project / ".xsolla-orchestrator/followup"
    followup.mkdir()
    atomic_json(followup / "plan.json", {**plan, "run_id": "followup", "tasks": [dict(tasks[0], state="planned")]})
    atomic_json(followup / "reused-context.json", memory.context(project, "implementation"))
    subprocess.run([sys.executable, str(Path(__file__).with_name("status.py")), str(run)], check=True, capture_output=True)
    return run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(create(args.output))
