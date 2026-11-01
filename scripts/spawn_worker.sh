#!/usr/bin/env bash
# Run one headless worker for a task, routed through the headroom proxy.
# Usage: spawn_worker.sh <run_dir> <task_id>
# Launch with Bash run_in_background; this script exits when the worker exits.
#
# Exit codes: 0 worker finished, 2 bad input, 3 headroom proxy unreachable,
# 5 run budget used up, other = claude's own exit code.
#
# Why not `headroom wrap claude`: wrap rewrites user config (it removes the
# Serena MCP entry under --code-memory none and writes a SessionStart hook into
# the project's .claude/settings.local.json). With the proxy already running,
# wrap --no-proxy only sets ANTHROPIC_BASE_URL and ENABLE_TOOL_SEARCH, so we set
# those directly and leave all config alone.
set -euo pipefail

RUN="$(cd "${1:?run_dir}" && pwd)"
TASK="${2:?task_id}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
source "$SKILL/scripts/lib.sh"
[ "${XSOLLA_DISPATCH_TASK:-}" = "$TASK" ] || { echo "Use scripts/dispatch.py to validate and reserve workers" >&2; exit 2; }
PLAN="$RUN/plan.json"
W="$RUN/workers/$TASK"
BRIEF="$W/brief.md"
REPORT="$W/report.md"

[ -f "$PLAN" ] || { echo "no plan.json in $RUN" >&2; exit 2; }
[ -s "$BRIEF" ] || { echo "missing or empty brief: $BRIEF" >&2; exit 2; }

IFS=$'\t' read -r MODEL EFFORT BUDGET ATTEMPT SKILLS RESUME RUN_ID PROJECT < <(task_field "$PLAN" "$TASK" \
  '"\t".join(str(x) for x in (t["model"], t["effort"], t.get("budget_usd", 3), t.get("attempt", 1),
   bool(t.get("skills")), t.get("resume_session") or "-", p["run_id"], p["project_dir"]))')
[ -n "${PROJECT:-}" ] || { echo "could not read routing for $TASK from plan.json" >&2; exit 2; }
ADD_DIRS=()
while IFS= read -r d; do [ -n "$d" ] && ADD_DIRS+=("$d"); done \
  < <(task_field "$PLAN" "$TASK" '"\n".join(t.get("add_dirs", []))')

# Run-wide budget gate.
RUN_BUDGET="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("run_budget_usd") or "")' "$PLAN")"
if [ -n "$RUN_BUDGET" ]; then
  SPENT="$(python3 "$SKILL/scripts/status.py" "$RUN" --spent)"
  if python3 -c 'import sys; sys.exit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)' "$SPENT" "$RUN_BUDGET"; then
    echo "run budget used up: \$$SPENT of \$$RUN_BUDGET; ask the user before spending more" >&2
    exit 5
  fi
fi

ROUTED=true
if ! proxy_ok; then
  if [ "${ORCH_ALLOW_UNWRAPPED:-0}" != "1" ]; then
    echo "headroom proxy not reachable on :$PORT; start it or set ORCH_ALLOW_UNWRAPPED=1" >&2
    exit 3
  fi
  ROUTED=false
fi

# Keep the previous attempt's records for the review trail.
PREV=$((ATTEMPT - 1))
[ -f "$W/log.jsonl" ] && mv "$W/log.jsonl" "$W/log.attempt$PREV.jsonl"
[ -f "$REPORT" ] && mv "$REPORT" "$W/report.attempt$PREV.md"
[ -f "$W/meta.json" ] && mv "$W/meta.json" "$W/meta.attempt$PREV.json"

# Snapshot the write list so a rejected attempt can be rolled back.
python3 "$SKILL/scripts/snapshot.py" "$RUN" "$TASK" save "$ATTEMPT" >/dev/null

build_deny
ALLOW=(Bash Read Edit Write Grep Glob NotebookEdit WebFetch WebSearch TodoWrite ToolSearch Skill mcp__headroom)
write_mcp "$W/mcp.json"

# Enforce the write list with a PreToolUse hook.
python3 - "$PLAN" "$TASK" "$W" > "$W/writes.json" <<'EOF'
import json, sys
p = json.load(open(sys.argv[1]))
t = next(x for x in p["tasks"] if x["id"] == sys.argv[2])
print(json.dumps({"root": p["project_dir"], "allow": t.get("writes", []), "always": [sys.argv[3] + "/"]}))
EOF
HOOK="$(python3 -c 'import shlex,sys; print(shlex.join([sys.executable, sys.argv[1]]))' "$SKILL/assets/hooks/guard_writes.py")"
SETTINGS="$(python3 -c 'import json,sys; print(json.dumps({"hooks":{"PreToolUse":[{"matcher":"Edit|Write|MultiEdit|NotebookEdit","hooks":[{"type":"command","command":sys.argv[1]}]}]}}))' "$HOOK")"

RULES="$(python3 - "$SKILL/assets/worker-rules.md" "$TASK" "$REPORT" <<'EOF'
import sys
text = open(sys.argv[1]).read()
print(text.replace("{{TASK_ID}}", sys.argv[2]).replace("{{REPORT_PATH}}", sys.argv[3]))
EOF
)"

# Lean startup: skills off and user-level settings skipped unless the task needs skills.
# Measured on sonnet: 22k -> ~9k startup tokens, and parallel workers share the cached prefix.
LEAN=(--exclude-dynamic-system-prompt-sections)
if [ "$SKILLS" = "True" ]; then
  LEAN+=(--setting-sources "user,project,local")
else
  LEAN+=(--disable-slash-commands --setting-sources "project,local")
fi
for d in "${ADD_DIRS[@]+"${ADD_DIRS[@]}"}"; do LEAN+=(--add-dir "$d"); done

# Same-tier retries resume the previous session (files already read stay cached);
# the prompt is then just the latest correction.
if [ "$RESUME" != "-" ]; then
  SESSION="$RESUME"
  SESSION_ARGS=(--resume "$RESUME")
  PROMPT="$(python3 - "$BRIEF" <<'EOF'
import re, sys
text = open(sys.argv[1]).read()
parts = re.split(r"\n(?=## Correction \(attempt \d+\))", text)
print(parts[-1] if len(parts) > 1 else text)
print("\nThe files are as you left them. Fix what the correction names, run the verify command, and rewrite your report.")
EOF
)"
else
  SESSION="$(uuidgen | tr '[:upper:]' '[:lower:]')"
  SESSION_ARGS=(--session-id "$SESSION")
  PROMPT="$(cat "$BRIEF")"
fi

PROMPT="$PROMPT

## Dispatch context
$(cat "$W/dispatch-context.json")"

TAG="xsolla-orch-$RUN_ID-$TASK"
ENV=(PATH="$SKILL/assets/bin:$PATH" ORCHESTRATE_WORKER="$TASK" ORCH_WRITES_FILE="$W/writes.json")
$ROUTED && ENV+=(ANTHROPIC_BASE_URL="$(base_url "$TAG")" ENABLE_TOOL_SEARCH=true)

json_set "$W/meta.json" runtime=headless "model=$MODEL" "effort=$EFFORT" "budget_usd=$BUDGET" \
  "attempt=$ATTEMPT" "routed=$ROUTED" "headroom_tag=$TAG" "resumed_from=$RESUME" "started_at=$(date +%s)" \
  "session_id=$SESSION"  # recorded up front: a paused or stopped worker never reports it

# --max-budget-usd is the task's checkpoint, not a limit: reaching it ends this process
# with error_max_budget_usd, and a healthy worker is resumed in the same session past it.
cd "$PROJECT"
set +e
env "${ENV[@]}" claude -p "$PROMPT" \
  --model "$MODEL" --effort "$EFFORT" \
  "${SESSION_ARGS[@]}" \
  --permission-mode acceptEdits \
  --allowedTools "${ALLOW[@]}" \
  --disallowedTools "${DENY[@]}" \
  --settings "$SETTINGS" \
  --strict-mcp-config --mcp-config "$W/mcp.json" \
  --max-budget-usd "$BUDGET" \
  --append-system-prompt "$RULES" \
  "${LEAN[@]}" \
  --output-format stream-json --verbose \
  < /dev/null > "$W/log.jsonl" 2> "$W/stderr.txt" &
PID=$!
json_set "$W/meta.json" "pid=$PID"
# The watchdog pauses the worker if it loops, keeps erroring, fights its guardrails,
# stops making progress or hangs. Spend alone never stops it (see the checkpoint below).
rm -f "$W/watchdog.json"
python3 "$SKILL/scripts/watchdog.py" "$RUN" "$TASK" --follow >/dev/null 2>&1 &
WATCHDOG=$!
wait "$PID"
CODE=$?
kill "$WATCHDOG" 2>/dev/null || true
set -e

IFS=$'\t' read -r SUBTYPE COST SID TEXT < <(last_result "$W/log.jsonl") || true
json_set "$W/meta.json" "ended_at=$(date +%s)" "exit_code=$CODE" "result=${SUBTYPE:-none}"
[ -n "${SID:-}" ] && json_set "$W/meta.json" "session_id=$SID"
echo "worker $TASK attempt $ATTEMPT exited $CODE ($MODEL/$EFFORT, routed=$ROUTED, ${SUBTYPE:-no result}, \$${COST:-0})"
[ -n "${TEXT:-}" ] && echo "result: $TEXT"
exit "$CODE"
