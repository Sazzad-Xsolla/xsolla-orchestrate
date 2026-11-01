#!/usr/bin/env python3
"""PreToolUse hook for orchestrate workers: block edits outside the task's write list.

spawn_worker.sh points ORCH_WRITES_FILE at a JSON file:
  {"root": "<project dir>", "allow": ["src/a.py", "docs/", "/abs/other/file"], "always": ["<worker dir>/"]}
Entries ending in "/" allow everything under that folder. Exit 2 blocks the call and
shows the message to the worker.
"""
import json
import os
import sys


def allowed(path, root, entries):
    for e in entries:
        target = e if os.path.isabs(e) else os.path.join(root, e)
        target = os.path.realpath(target.rstrip("/")) + ("/" if e.endswith("/") else "")
        if target.endswith("/"):
            if path.startswith(target) or path == target.rstrip("/"):
                return True
        elif path == target:
            return True
    return False


def main():
    try:
        event = json.load(sys.stdin)
        spec = json.load(open(os.environ["ORCH_WRITES_FILE"]))
    except (OSError, KeyError, ValueError):
        return 0  # no spec: nothing to enforce
    inp = event.get("tool_input") or {}
    raw = inp.get("file_path") or inp.get("notebook_path") or inp.get("path")
    if not raw:
        return 0
    cwd = event.get("cwd") or spec["root"]
    path = os.path.realpath(raw if os.path.isabs(raw) else os.path.join(cwd, raw))
    if allowed(path, spec["root"], spec.get("allow", []) + spec.get("always", [])):
        return 0
    print(f"BLOCKED by orchestrator: {raw} is not in this task's write list "
          f"({', '.join(spec.get('allow', [])) or 'nothing'}). If it must change, say so in your report.",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
