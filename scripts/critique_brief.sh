#!/usr/bin/env bash
# Cold-read a task brief with a fresh sonnet worker before dispatch.
# Usage: critique_brief.sh <run_dir> <task_id>
# Writes workers/<id>/critique.md. Exit 0 = clear, 10 = needs fixes, other = error.
set -euo pipefail

RUN="$(cd "${1:?run_dir}" && pwd)"
TASK="${2:?task_id}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
source "$SKILL/scripts/lib.sh"
python3 "$SKILL/scripts/dispatch_approval.py" "$RUN" check >/dev/null
W="$RUN/workers/$TASK"
[ -s "$W/brief.md" ] || { echo "missing brief: $W/brief.md" >&2; exit 2; }

PROJECT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["project_dir"])' "$RUN/plan.json")"
RUN_ID="$(basename "$RUN")"
write_mcp "$W/critic-mcp.json"

ENV=(PATH="$SKILL/assets/bin:$PATH")
proxy_ok && ENV+=(ANTHROPIC_BASE_URL="$(base_url "orch-$RUN_ID-$TASK-critic")" ENABLE_TOOL_SEARCH=true)

FINGERPRINT="$(python3 "$SKILL/scripts/dispatch.py" "$RUN" "$TASK" --fingerprint)"
PROMPT="$(cat "$SKILL/assets/critic-prompt.md")

---
# The brief to review

$(cat "$W/brief.md")"

cd "$PROJECT"
set +e
env "${ENV[@]}" claude -p "$PROMPT" \
  --model "${ORCH_CRITIC_MODEL:-sonnet}" --effort low \
  --permission-mode default --allowedTools Read Grep Glob \
  --strict-mcp-config --mcp-config "$W/critic-mcp.json" \
  --disable-slash-commands --setting-sources "project,local" --exclude-dynamic-system-prompt-sections \
  --max-budget-usd 0.5 --output-format json \
  < /dev/null > "$W/critique.json" 2> "$W/critique.stderr"
CODE=$?
set -e
[ "$CODE" -eq 0 ] || { echo "critic failed (exit $CODE); see $W/critique.stderr" >&2; exit "$CODE"; }

python3 - "$W/critique.json" "$W/critique.md" "$SKILL/scripts" "$RUN" "$TASK" "$FINGERPRINT" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
text = d.get("result") or ""
open(sys.argv[2], "w").write(text + "\n")
cost = d.get("total_cost_usd") or 0
verdict = "needs-fixes" if "VERDICT: needs-fixes" in text else ("clear" if "VERDICT: clear" in text else "unknown")
print(f"critic verdict: {verdict} (${cost:.3f})")
sys.path.insert(0, sys.argv[3])
from control import atomic_json, load_run, task_by_id, now
from dispatch import critique_fingerprint
run, plan, _ = load_run(sys.argv[4])
task = task_by_id(plan, sys.argv[5])
atomic_json(run / "workers" / task["id"] / "critique-audit.json", {
    "verdict": verdict, "at": now(), "fingerprint": sys.argv[6]})
sys.exit(0 if verdict == "clear" else 10)
EOF
