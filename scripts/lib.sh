# Shared helpers for orchestrate scripts. Source it; don't run it.
# Expects SKILL to be set by the caller.

PORT="${HEADROOM_PORT:-8787}"

# proxy_ok: true when the headroom proxy answers its health check.
proxy_ok() {
  curl -sf -m 3 "http://127.0.0.1:$PORT/health" >/dev/null
}

# build_deny: fills the DENY array from assets/deny.txt, adding an "rtk "-prefixed
# copy of every Bash(...) rule because the user's rtk hook rewrites commands.
build_deny() {
  DENY=()
  local rule
  while IFS= read -r rule; do
    case "$rule" in ''|'#'*) continue ;; esac
    DENY+=("$rule")
    case "$rule" in Bash\(*) DENY+=("Bash(rtk ${rule#Bash(}") ;; esac
  done < "$SKILL/assets/deny.txt"
}

# write_mcp <file>: worker MCP config with only the headroom server.
write_mcp() {
  python3 - "$1" "$(command -v headroom || true)" <<'EOF'
import json, sys
servers = {"headroom": {"type": "stdio", "command": sys.argv[2], "args": ["mcp", "serve"]}} if sys.argv[2] else {}
with open(sys.argv[1], "w") as stream:
    json.dump({"mcpServers": servers}, stream)
EOF
}

# base_url <tag>: proxy URL that attributes savings to <tag> in headroom's per_project stats.
base_url() {
  local tag
  tag="$(printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '-' | cut -c1-120)"
  echo "http://127.0.0.1:$PORT/p/$tag"
}

# task_field <plan> <task> <python-expr over t and p>: print one value from plan.json.
task_field() {
  python3 - "$1" "$2" "$3" <<'EOF'
import json, sys
p = json.load(open(sys.argv[1]))
t = next((x for x in p["tasks"] if x["id"] == sys.argv[2]), None)
if t is None:
    sys.exit(f"task {sys.argv[2]} not in plan.json")
v = eval(sys.argv[3], {}, {"t": t, "p": p})
print("" if v is None else (json.dumps(v) if isinstance(v, (list, dict, bool)) else v))
EOF
}

# json_set <file> key=value...: merge keys into a JSON object file (values parsed as JSON when possible).
json_set() {
  PYTHONPATH="$SKILL/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 - "$@" <<'EOF'
import json, sys
from control import locked_json
path, *kv = sys.argv[1:]
with locked_json(path, {}) as data:
    for item in kv:
        key, value = item.split("=", 1)
        try:
            value = json.loads(value)
        except ValueError:
            pass
        data[key] = value
EOF
}

# last_result <log.jsonl>: print "subtype<TAB>cost<TAB>session_id<TAB>text" of the final result event.
last_result() {
  python3 - "$1" <<'EOF'
import json, sys
last = None
for line in open(sys.argv[1], errors="replace"):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("type") == "result":
        last = e
if last:
    text = (last.get("result") or "").replace("\n", " ")[:300]
    print(f"{last.get('subtype')}\t{last.get('total_cost_usd') or 0:.4f}\t{last.get('session_id')}\t{text}")
EOF
}
