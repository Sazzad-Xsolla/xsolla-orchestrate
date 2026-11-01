#!/usr/bin/env bash
# Create a run folder for an orchestrate run and print its absolute path.
# Usage: init_run.sh <project_dir> <slug> [--template NAME] [--budget USD] [--var KEY=VALUE]...
#   --template  start from templates/NAME.json (tasks + draft briefs with {{KEY}} placeholders)
#   --budget    run-wide spend cap in USD; spawn_worker.sh refuses to start workers past it
#   --var       fill a template placeholder, e.g. --var UC=UC-01
set -euo pipefail

PROJECT="$(cd "${1:?project_dir}" && pwd)"
SLUG="$(printf '%s' "${2:?slug}" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-')"
shift 2
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
source "$SKILL/scripts/lib.sh"

TEMPLATE="" BUDGET="" VARS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --template) TEMPLATE="$2"; shift 2 ;;
    --budget) BUDGET="$2"; shift 2 ;;
    --var) VARS+=("$2"); shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
if [ -n "$TEMPLATE" ] && [ ! -f "$SKILL/templates/$TEMPLATE.json" ]; then
  echo "no template '$TEMPLATE'. Available: $(ls "$SKILL/templates" | sed 's/\.json$//' | tr '\n' ' ')" >&2
  exit 2
fi

RUN_ID="$(date +%Y%m%d-%H%M%S)-$SLUG-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:6])')"
RUN="$PROJECT/.xsolla-orchestrator/$RUN_ID"
mkdir -p "$RUN/workers"

# Keep run records local: exclude from git without touching the tracked .gitignore.
if GITDIR="$(git -C "$PROJECT" rev-parse --git-dir 2>/dev/null)"; then
  case "$GITDIR" in /*) ;; *) GITDIR="$PROJECT/$GITDIR" ;; esac
  EXCL="$GITDIR/info/exclude"
  mkdir -p "$(dirname "$EXCL")"
  grep -qxF '.xsolla-orchestrator/' "$EXCL" 2>/dev/null || echo '.xsolla-orchestrator/' >> "$EXCL"
fi

python3 - "$RUN" "$RUN_ID" "$PROJECT" "${TEMPLATE:+$SKILL/templates/$TEMPLATE.json}" "$BUDGET" "${VARS[@]+"${VARS[@]}"}" <<'EOF'
import json, re, subprocess, sys
from pathlib import Path
run, run_id, project, template, budget, *pairs = sys.argv[1:]
vars_ = dict(p.split("=", 1) for p in pairs)
vars_.setdefault("PROJECT", project)
vars_.setdefault("RUN", run)

def fill(text):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: vars_.get(m.group(1), m.group(0)), text)

# Files already dirty before the run, so status.py doesn't report them as drift.
dirty = []
try:
    out = subprocess.run(["git", "-C", project, "status", "--porcelain"], capture_output=True, text=True, timeout=10)
    if out.returncode == 0:
        dirty = [l[3:].split(" -> ")[-1].strip('"') for l in out.stdout.splitlines()]
except Exception:
    pass

plan = {
    "run_id": run_id, "title": "", "project_dir": project, "goal": "",
    "definition_of_done": [], "verification_plan": "",
    "run_budget_usd": float(budget) if budget else None,
    "git_dirty_at_start": dirty, "dashboard_url": None,
    "dashboard_theme": "xsolla", "dashboard": "off", "version": 1,
    "tasks": [], "approvals": [], "log": [],
}
unfilled = set()
if template:
    tpl = json.loads(fill(Path(template).read_text()))
    plan["template"] = Path(template).stem
    for t in tpl["tasks"]:
        brief = t.pop("brief", "")
        t.setdefault("state", "planned"); t.setdefault("attempt", 1); t.setdefault("routing_history", [])
        plan["tasks"].append(t)
        wdir = Path(run) / "workers" / t["id"]
        wdir.mkdir(parents=True, exist_ok=True)
        (wdir / "brief.md").write_text("<!-- DRAFT from template: fill every {{PLACEHOLDER}} and <angle-bracket> note before dispatch -->\n" + brief)
        unfilled |= set(re.findall(r"\{\{(\w+)\}\}", json.dumps(t) + brief))
json.dump(plan, open(f"{run}/plan.json", "w"), indent=2)
if unfilled:
    print(f"template placeholders still to fill: {', '.join(sorted(unfilled))}", file=sys.stderr)
EOF

proxy_ok || echo "warning: headroom proxy not reachable on :$PORT" >&2
echo "$RUN"
