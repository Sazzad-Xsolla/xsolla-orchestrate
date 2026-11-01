#!/usr/bin/env python3
"""Spot a worker going off the rails from its behaviour, not its spend.

Usage:
  watchdog.py <run_dir> <task_id>            check once; prints a JSON verdict
                                             (exit 0 healthy, 6 runaway)
  watchdog.py <run_dir> <task_id> --follow   run beside a live worker (spawn_worker.sh
                                             starts it); on a runaway signal it pauses
                                             the worker and writes workers/<id>/watchdog.json

Pausing stops the process but keeps its files and its session, so it can be resumed
exactly where it was. Signals and their thresholds are in SIGNALS below.
"""
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent

# Thresholds: deliberately loose. A worker doing real, varied work never trips these.
SIGNALS = {
    "repeat_call": 5,      # the same tool call this many times in the last 20, with no successful edit in between
    "error_streak": 8,     # this many tool errors in a row
    "guard_fights": 3,     # blocked writes + denied commands; it keeps trying to leave its lane
    "no_progress": 40,     # turns since its last successful edit to its own files (tasks with a write list)
    "stall_minutes": 10,   # no new output from a live worker for this long
}
POLL_SECONDS = 5  # reading a log is cheap; a fast loop can burn 12 calls in 20 s
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def call_key(tool):
    inp = tool.get("input", {})
    detail = inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp.get("url") or json.dumps(inp, sort_keys=True)
    if tool.get("name") in EDIT_TOOLS:
        # an edit with different content is real work, not a loop
        detail = f"{detail}::{hash(json.dumps(inp, sort_keys=True))}"
    return f"{tool.get('name')}::{str(detail).strip()[:300]}"


def analyze(log_path, writes, report_dir):
    calls, results = [], {}
    turns = last_edit_turn = 0
    blocked = 0
    if not log_path.exists():
        return {"healthy": True, "signals": [], "turns": 0}
    for line in log_path.read_text(errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        msg = e.get("message") or {}
        content = msg.get("content") if isinstance(msg.get("content"), list) else []
        if e.get("type") == "assistant":
            turns += 1
            for c in content:
                if c.get("type") == "tool_use":
                    calls.append({"id": c.get("id"), "name": c.get("name"), "key": call_key(c),
                                  "path": (c.get("input") or {}).get("file_path", ""), "turn": turns})
        elif e.get("type") == "user":
            for c in content:
                if c.get("type") == "tool_result":
                    text = str(c.get("content"))
                    err = bool(c.get("is_error")) or "BLOCKED by orchestrator" in text or "has been denied" in text
                    results[c.get("tool_use_id")] = err
                    if "BLOCKED by orchestrator" in text or "has been denied" in text:
                        blocked += 1

    signals = []
    # A loop is the same call repeated with nothing changing in between. Edit -> run tests ->
    # edit -> run tests is normal work, so a successful edit resets the count.
    since_edit = []
    for c in calls[-20:]:
        if c["name"] in EDIT_TOOLS and results.get(c["id"]) is False:
            since_edit = []
        else:
            since_edit.append(c["key"])
    recent = Counter(since_edit)
    if recent:
        key, n = recent.most_common(1)[0]
        if n >= SIGNALS["repeat_call"]:
            signals.append({"signal": "repeat_call", "detail": f"the same call {n} times with nothing changed in between: {key.split('::', 1)[1][:120]}"})

    streak = 0
    for c in calls:
        if c["id"] in results:
            streak = streak + 1 if results[c["id"]] else 0
    if streak >= SIGNALS["error_streak"]:
        signals.append({"signal": "error_streak", "detail": f"{streak} tool errors in a row"})

    if blocked >= SIGNALS["guard_fights"]:
        signals.append({"signal": "guard_fights", "detail": f"{blocked} blocked writes or denied commands"})

    if writes:
        for c in calls:
            if c["name"] in EDIT_TOOLS and results.get(c["id"]) is False and not c["path"].startswith(report_dir):
                last_edit_turn = c["turn"]
        if turns - last_edit_turn >= SIGNALS["no_progress"]:
            signals.append({"signal": "no_progress", "detail": f"{turns - last_edit_turn} turns without a successful edit to its files"})

    return {"healthy": not signals, "signals": signals, "turns": turns}


def load(run, task_id):
    plan = json.loads((run / "plan.json").read_text())
    task = next(t for t in plan["tasks"] if t["id"] == task_id)
    return task, run / "workers" / task_id


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def follow(run, task_id):
    task, wdir = load(run, task_id)
    meta_path = wdir / "meta.json"
    while True:
        time.sleep(POLL_SECONDS)
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        if "ended_at" in meta or not pid_alive(meta.get("pid")):
            return
        verdict = analyze(wdir / "log.jsonl", task.get("writes", []), str(wdir))
        log = wdir / "log.jsonl"
        if log.exists() and time.time() - log.stat().st_mtime > SIGNALS["stall_minutes"] * 60:
            verdict["signals"].append({"signal": "stall", "detail": f"no output for {SIGNALS['stall_minutes']}+ minutes"})
            verdict["healthy"] = False
        if not verdict["healthy"]:
            first = verdict["signals"][0]
            (wdir / "watchdog.json").write_text(json.dumps({**verdict, "at": time.strftime("%H:%M:%S"),
                                                            "attempt": task.get("attempt", 1)}, indent=2))
            subprocess.run(["bash", str(SKILL / "scripts" / "stop_worker.sh"), str(run), task_id,
                            f"paused by watchdog: {first['detail']}", "paused"], capture_output=True, timeout=30)
            return


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    run, task_id = Path(sys.argv[1]).resolve(), sys.argv[2]
    if "--follow" in sys.argv:
        follow(run, task_id)
        return
    task, wdir = load(run, task_id)
    verdict = analyze(wdir / "log.jsonl", task.get("writes", []), str(wdir))
    print(json.dumps(verdict, indent=2))
    sys.exit(0 if verdict["healthy"] else 6)


if __name__ == "__main__":
    main()
