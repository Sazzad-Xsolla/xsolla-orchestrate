#!/usr/bin/env bash
# Stop a running headless worker. Its files and session are kept, so it can be resumed.
# Usage: stop_worker.sh <run_dir> <task_id> [reason] [state]
#   state: what to mark the task (default "failed"; the watchdog uses "paused")
set -euo pipefail

RUN="$(cd "${1:?run_dir}" && pwd)"
TASK="${2:?task_id}"
REASON="${3:-stopped by orchestrator}"
STATE="${4:-failed}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
source "$SKILL/scripts/lib.sh"
META="$RUN/workers/$TASK/meta.json"

PID="$(python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); print("" if "ended_at" in m else m.get("pid",""))' "$META" 2>/dev/null || true)"
if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
  echo "$TASK is not running"
  exit 0
fi

# Record the intended state before interrupting so dispatch cleanup preserves pauses.
json_set "$META" "killed=true" "kill_reason=$REASON"
PYTHONPATH="$SKILL/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 - "$RUN/plan.json" "$TASK" "$REASON" "$STATE" <<'EOF'
import sys, time
from control import locked_json, task_by_id
path, task_id, reason, state = sys.argv[1:5]
with locked_json(path) as plan:
    task_by_id(plan, task_id)["state"] = state
    plan.setdefault("log", []).append({"at": time.strftime("%H:%M"), "note": f"{task_id} stopped: {reason}"})
EOF

# Interrupt first: claude -p then writes its final result event, so the exact cost of
# the stopped attempt is kept. Escalate only if it hasn't exited.
kill -INT "$PID" 2>/dev/null || true
for _ in $(seq 1 15); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
if kill -0 "$PID" 2>/dev/null; then
  kill -TERM "$PID" 2>/dev/null || true
  for _ in 1 2 3 4 5; do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
  kill -0 "$PID" 2>/dev/null && kill -KILL "$PID" 2>/dev/null || true
fi

echo "stopped $TASK (pid $PID): $REASON"
