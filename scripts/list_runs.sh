#!/usr/bin/env bash
# List project runs without splitting paths on spaces.
set -euo pipefail
python3 - "${1:-.}" <<'EOF'
import json, sys
from pathlib import Path
project = Path(sys.argv[1]).resolve()
plans = sorted((project / ".xsolla-orchestrator").glob("*/plan.json"), key=lambda p: p.stat().st_mtime, reverse=True)
if not plans:
    print("No Xsolla runs in " + str(project))
for path in plans:
    plan = json.loads(path.read_text())
    states = [task.get("state", "planned") for task in plan.get("tasks", [])]
    summary = ", ".join(f"{states.count(state)} {state}" for state in dict.fromkeys(states)) or "no tasks"
    print(str(path.parent) + "\n  " + (plan.get("title") or plan["run_id"]) + ": " + summary)
EOF
